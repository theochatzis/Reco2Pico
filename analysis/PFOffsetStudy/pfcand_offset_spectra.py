#!/usr/bin/env python3
"""
Study event-by-event PicoAOD PF-candidate pT spectra in eta rings.

The default is intentionally ONE EVENT PER FILE (event 0), matching the
information available to PUPPI when it computes its weights.

For each particle category and eta ring the script studies both

    pT
    puppiWeight * pT

and overlays the distributions from different input Pico files.

Typical branches:
    PFCand_pt
    PFCand_eta
    PFCand_pdgId
    PFCand_charge          (optional)
    PFCand_puppiWeight     (auto-detected; can be overridden)
:wq
Example
-------
python3 pfcand_offset_spectra.py data.root mc.root \
    --labels Data DY \
    --event 0 \
    --eta-bins -5.2 -3.0 -2.5 -1.5 0 1.5 2.5 3.0 5.2 \
    --pt-max 10 \
    --output-dir pfcand_offset_study

By default the overlaid histograms are normalized to unit area, because the
goal is to compare shapes.  Use --counts to compare absolute candidate counts.

To aggregate all events instead:
    python3 pfcand_offset_spectra.py file1.root file2.root --all-events
"""
import argparse
import csv
from pathlib import Path
from array import array

import ROOT

CATEGORY_NAMES = [
    "chargedHadron",
    "neutralHadron",
    "photon",
    "electron",
    "muon",
    "HFHadron",
    "HFEM",
    "other",
]

CATEGORY_LABELS = {
    "chargedHadron": "charged hadrons",
    "neutralHadron": "neutral hadrons",
    "photon": "photons",
    "electron": "electrons",
    "muon": "muons",
    "HFHadron": "HF hadrons",
    "HFEM": "HF electromagnetic",
    "other": "other",
}

WEIGHT_CANDIDATES = [
    "{c}_puppiWeight",
    "{c}_puppi_weight",
    "{c}_puppiWeightNoLep",
    "{c}_puppi_weightNoLep",
    "{c}_PuppiWeight",
    "{c}_PUPPIWeight",
]

NVTX_CANDIDATES = [
    "PV_npvs",
    "PV_npvsGood",
    "nPV",
    "nPVGood",
    "nVertex",
    "nVertices",
]


def parse_args():
    p = argparse.ArgumentParser(
        description="Fast per-event PFCand pT study using ROOT RDataFrame."
    )
    p.add_argument("inputs", nargs="+")
    p.add_argument("--labels", nargs="+", default=None)
    p.add_argument("--tree", default="Events")
    p.add_argument("--collection", default="PFCand")
    p.add_argument("--event", type=int, default=0)
    p.add_argument("--all-events", action="store_true")
    p.add_argument("--max-events", type=int, default=-1)
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--puppi-weight-branch", default=None)
    p.add_argument(
        "--nvtx-branch",
        default=None,
        help="Explicit vertex-count branch; otherwise auto-detected (PV_npvs preferred)",
    )
    p.add_argument(
        "--min-nvtx",
        type=float,
        default=None,
        help=(
            "In single-event mode, start from --event and select the first event "
            "with Nvtx strictly greater than this value"
        ),
    )
    p.add_argument("--nvtx-min", type=float, default=0.0)
    p.add_argument("--nvtx-max", type=float, default=100.0)
    p.add_argument("--n-nvtx-bins", type=int, default=100)
    p.add_argument(
        "--eta-bins",
        nargs="+",
        type=float,
        default=[-5.2, -3.0, -2.5, -1.5, 0.0, 1.5, 2.5, 3.0, 5.2],
    )
    p.add_argument("--absolute-eta", action="store_true")
    p.add_argument(
        "--categories",
        nargs="+",
        choices=CATEGORY_NAMES,
        default=CATEGORY_NAMES,
    )
    p.add_argument("--pt-min", type=float, default=0.0)
    p.add_argument("--pt-max", type=float, default=10.0)
    p.add_argument("--n-pt-bins", type=int, default=80)
    p.add_argument("--counts", action="store_true")
    p.add_argument("--linear-only", action="store_true")
    p.add_argument("--raw-vs-puppi", action="store_true")
    p.add_argument("--save-root", action="store_true")
    p.add_argument("--output-dir", default="pfcand_offset_rdf")
    return p.parse_args()


def validate(args):
    if args.event < 0:
        raise ValueError("--event must be >= 0")
    if args.pt_max <= args.pt_min:
        raise ValueError("--pt-max must be > --pt-min")
    if args.nvtx_max <= args.nvtx_min:
        raise ValueError("--nvtx-max must be > --nvtx-min")
    if args.n_nvtx_bins <= 0:
        raise ValueError("--n-nvtx-bins must be > 0")
    if args.all_events and args.min_nvtx is not None:
        raise ValueError("--min-nvtx is only meaningful in single-event mode")
    if args.labels is not None and len(args.labels) != len(args.inputs):
        raise ValueError("--labels must match the number of input files")
    edges = list(map(float, args.eta_bins))
    if len(edges) < 2 or any(b <= a for a, b in zip(edges[:-1], edges[1:])):
        raise ValueError("--eta-bins must be strictly increasing")
    if args.absolute_eta and any(x < 0 for x in edges):
        raise ValueError("--absolute-eta requires non-negative eta edges")
    return edges


def progress(iterable, total, desc):
    try:
        from tqdm import tqdm
        return tqdm(iterable, total=total, desc=desc)
    except ImportError:
        def gen():
            for i, item in enumerate(iterable, 1):
                width = 28
                n = int(width * i / max(total, 1))
                print(
                    f"\r{desc}: [{'#' * n}{'-' * (width - n)}] {i}/{total}",
                    end="",
                    flush=True,
                )
                yield item
            print()
        return gen()


def declare_helpers():
    ROOT.gInterpreter.Declare(r'''
#include <ROOT/RVec.hxx>
#include <algorithm>
#include <cmath>
#include <vector>

namespace PhiOffsetStudy {

template <typename VPdg, typename VCharge, typename VEta>
ROOT::VecOps::RVec<int> binIndex(const VPdg& pdgId,
                                 const VCharge& charge,
                                 const VEta& eta,
                                 const std::vector<double>& etaEdges,
                                 bool useAbsEta) {
  const std::size_t n = pdgId.size();
  ROOT::VecOps::RVec<int> out(n, -1);
  if (eta.size() != n || charge.size() != n || etaEdges.size() < 2)
    return out;

  const int nEta = static_cast<int>(etaEdges.size()) - 1;

  for (std::size_t i = 0; i < n; ++i) {
    const int pid = static_cast<int>(pdgId[i]);
    const int apid = std::abs(pid);
    int category = 7;

    // Offset-study classification:
    //
    //   charged candidates:
    //     electron PID -> electron
    //     muon PID     -> muon
    //     otherwise    -> chargedHadron
    //
    //   neutral candidates:
    //     photon PID   -> photon
    //     PF HF type 1 -> HFHadron
    //     PF HF type 2 -> HFEM
    //     otherwise    -> neutralHadron
    //
    // Charge is therefore the primary charged/neutral discriminator.
    if (apid == 11) {
      category = 3;
    } else if (apid == 13) {
      category = 4;
    } else if (charge[i] != 0) {
      category = 0;
    } else if (pid == 22) {
      category = 2;
    } else if (pid == 1) {
      category = 5;
    } else if (pid == 2) {
      category = 6;
    } else {
      category = 1;
    }

    const double x = useAbsEta ? std::abs(static_cast<double>(eta[i]))
                               : static_cast<double>(eta[i]);
    const auto it = std::upper_bound(etaEdges.begin(), etaEdges.end(), x);
    if (it == etaEdges.begin() || it == etaEdges.end())
      continue;

    const int ieta = static_cast<int>(std::distance(etaEdges.begin(), it)) - 1;
    out[i] = category * nEta + ieta;
  }
  return out;
}

template <typename VPdg, typename VEta>
ROOT::VecOps::RVec<int> binIndexNoCharge(const VPdg& pdgId,
                                         const VEta& eta,
                                         const std::vector<double>& etaEdges,
                                         bool useAbsEta) {
  const std::size_t n = pdgId.size();
  ROOT::VecOps::RVec<int> out(n, -1);
  if (eta.size() != n || etaEdges.size() < 2)
    return out;

  const int nEta = static_cast<int>(etaEdges.size()) - 1;

  for (std::size_t i = 0; i < n; ++i) {
    const int pid = static_cast<int>(pdgId[i]);
    const int apid = std::abs(pid);
    int category = 7;

    // This branch is used only when PFCand_charge is not available.
    // In that case we cannot use the preferred charge-first definition and
    // must fall back to the PF/PID information.
    if (pid == 1) category = 5;
    else if (pid == 2) category = 6;
    else if (apid == 11) category = 3;
    else if (apid == 13) category = 4;
    else if (apid == 22) category = 2;
    else if (pid == 130) category = 1;
    else if (apid == 211) category = 0;
    else {
      // Fallback for non-standard IDs if charge is not stored.
      const bool charged =
          apid == 321 || apid == 2212 ||
          apid == 3112 || apid == 3222 || apid == 3312 || apid == 3334;
      const bool neutral =
          apid == 2112 || apid == 310 ||
          apid == 3122 || apid == 3322;
      if (charged) category = 0;
      else if (neutral) category = 1;
    }

    const double x = useAbsEta ? std::abs(static_cast<double>(eta[i]))
                               : static_cast<double>(eta[i]);
    const auto it = std::upper_bound(etaEdges.begin(), etaEdges.end(), x);
    if (it == etaEdges.begin() || it == etaEdges.end())
      continue;

    const int ieta = static_cast<int>(std::distance(etaEdges.begin(), it)) - 1;
    out[i] = category * nEta + ieta;
  }
  return out;
}

}
''')


def tree_info(filename, tree_name):
    f = ROOT.TFile.Open(filename)
    if not f or f.IsZombie():
        raise RuntimeError(f"Cannot open {filename}")
    t = f.Get(tree_name)
    if not t:
        f.Close()
        raise RuntimeError(f"{filename}: tree {tree_name} not found")
    branches = {b.GetName() for b in t.GetListOfBranches()}
    entries = int(t.GetEntries())
    f.Close()
    return branches, entries


def detect_weight(branches, collection, explicit):
    if explicit:
        if explicit not in branches:
            raise RuntimeError(f"PUPPI branch {explicit} not found")
        return explicit
    for pattern in WEIGHT_CANDIDATES:
        name = pattern.format(c=collection)
        if name in branches:
            return name
    matches = sorted(
        b for b in branches
        if b.lower().startswith(collection.lower() + "_")
        and "puppi" in b.lower()
        and "weight" in b.lower()
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(
            "Several PUPPI weight branches found: "
            + ", ".join(matches)
            + ". Use --puppi-weight-branch."
        )
    raise RuntimeError("Could not auto-detect a PUPPI weight branch")


def detect_nvtx(branches, explicit):
    if explicit:
        if explicit not in branches:
            raise RuntimeError(f"Nvtx branch {explicit} not found")
        return explicit

    for name in NVTX_CANDIDATES:
        if name in branches:
            return name

    matches = sorted(
        b for b in branches
        if ("npv" in b.lower() or "nvtx" in b.lower() or "nvert" in b.lower())
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(
            "Several possible Nvtx branches found: "
            + ", ".join(matches)
            + ". Use --nvtx-branch."
        )
    raise RuntimeError(
        "Could not auto-detect an Nvtx branch. Use --nvtx-branch explicitly."
    )


def scalar_branch_value(tree, branch_name):
    """Read a scalar ROOT branch numerically.

    Do not use getattr(tree, branch_name) here: NanoAOD/Pico branches such as
    PV_npvs can be stored as UChar_t, which PyROOT may expose as a one-character
    Python string (e.g. '#' for the numeric value 35).

    TLeaf::GetValue() always converts scalar fundamental ROOT types to a
    numeric double, which is exactly what is needed for the Nvtx selection.
    """
    leaf = tree.GetLeaf(branch_name)

    if not leaf:
        branch = tree.GetBranch(branch_name)
        if branch:
            leaves = branch.GetListOfLeaves()
            if leaves and leaves.GetEntries() == 1:
                leaf = leaves.At(0)

    if not leaf:
        raise RuntimeError(
            f"Could not get a scalar TLeaf for branch '{branch_name}'"
        )

    return float(leaf.GetValue(0))


def find_selected_event(filename, tree_name, nvtx_branch, start_event, min_nvtx):
    """Return (entry, Nvtx), starting at start_event.

    The search reads only the scalar Nvtx branch. The heavy PFCand work remains
    in RDataFrame. If min_nvtx is None, no search is performed.
    """
    f = ROOT.TFile.Open(filename)
    if not f or f.IsZombie():
        raise RuntimeError(f"Cannot open {filename}")
    tree = f.Get(tree_name)
    if not tree:
        f.Close()
        raise RuntimeError(f"{filename}: tree {tree_name} not found")

    nentries = int(tree.GetEntries())
    if start_event >= nentries:
        f.Close()
        raise RuntimeError(
            f"{filename}: requested start event {start_event}, only {nentries} entries exist"
        )

    tree.SetBranchStatus("*", 0)
    tree.SetBranchStatus(nvtx_branch, 1)

    if min_nvtx is None:
        tree.GetEntry(start_event)
        nvtx = scalar_branch_value(tree, nvtx_branch)
        f.Close()
        return start_event, nvtx

    for entry in range(start_event, nentries):
        tree.GetEntry(entry)
        nvtx = scalar_branch_value(tree, nvtx_branch)
        if nvtx > min_nvtx:
            f.Close()
            return entry, nvtx

    f.Close()
    raise RuntimeError(
        f"{filename}: no event at or after entry {start_event} has "
        f"{nvtx_branch} > {min_nvtx}"
    )


def edge_expr(edges):
    return "std::vector<double>{" + ",".join(f"{x:.17g}" for x in edges) + "}"


def make_sample(filename, label, args, edges, idx):
    branches, nentries = tree_info(filename, args.tree)

    pt = f"{args.collection}_pt"
    eta = f"{args.collection}_eta"
    pdgid = f"{args.collection}_pdgId"
    charge = f"{args.collection}_charge"

    for b in (pt, eta, pdgid):
        if b not in branches:
            raise RuntimeError(f"{filename}: missing branch {b}")

    weight = detect_weight(branches, args.collection, args.puppi_weight_branch)
    nvtx = detect_nvtx(branches, args.nvtx_branch)

    selected_event = None
    selected_nvtx = None
    if not args.all_events:
        selected_event, selected_nvtx = find_selected_event(
            filename,
            args.tree,
            nvtx,
            args.event,
            args.min_nvtx,
        )

    # Event-level Nvtx distribution. In single-event mode this intentionally
    # uses the full file, while the PFCand spectra below use one selected event.
    df_nvtx = ROOT.RDataFrame(args.tree, filename)
    if args.all_events and args.max_events >= 0:
        df_nvtx = df_nvtx.Range(0, min(args.max_events, nentries))

    nvtx_model = ROOT.RDF.TH1DModel(
        f"h_nvtx_{idx}",
        "",
        args.n_nvtx_bins,
        args.nvtx_min,
        args.nvtx_max,
    )
    h_nvtx = df_nvtx.Histo1D(nvtx_model, nvtx)

    df = ROOT.RDataFrame(args.tree, filename)

    if not args.all_events:
        df = df.Range(selected_event, selected_event + 1)
    elif args.max_events >= 0:
        df = df.Range(0, min(args.max_events, nentries))

    eexpr = edge_expr(edges)
    aexpr = "true" if args.absolute_eta else "false"

    if charge in branches:
        bexpr = (
            f"PhiOffsetStudy::binIndex({pdgid}, {charge}, {eta}, "
            f"{eexpr}, {aexpr})"
        )
    else:
        bexpr = (
            f"PhiOffsetStudy::binIndexNoCharge({pdgid}, {eta}, "
            f"{eexpr}, {aexpr})"
        )

    df = (
        df.Define("PhiStudy_bin", bexpr)
          .Define("PhiStudy_puppiPt", f"{pt} * {weight}")
    )

    n_eta = len(edges) - 1
    ny = len(CATEGORY_NAMES) * n_eta

    raw_model = ROOT.RDF.TH2DModel(
        f"h2_raw_{idx}", "",
        args.n_pt_bins, args.pt_min, args.pt_max,
        ny, -0.5, ny - 0.5,
    )
    pup_model = ROOT.RDF.TH2DModel(
        f"h2_puppi_{idx}", "",
        args.n_pt_bins, args.pt_min, args.pt_max,
        ny, -0.5, ny - 0.5,
    )

    multiplicity_model = ROOT.RDF.TH1DModel(
        f"h_category_eta_multiplicity_{idx}",
        "",
        ny,
        -0.5,
        ny - 0.5,
    )

    return {
        "filename": filename,
        "label": label,
        "weight": weight,
        "nvtx_branch": nvtx,
        "selected_event": selected_event,
        "selected_nvtx": selected_nvtx,
        "h_nvtx": h_nvtx,
        "h2_raw": df.Histo2D(raw_model, pt, "PhiStudy_bin"),
        "h2_puppi": df.Histo2D(pup_model, "PhiStudy_puppiPt", "PhiStudy_bin"),
        # Counts all PFCands irrespective of the pT plotting range.
        "h_category_eta_multiplicity": df.Histo1D(
            multiplicity_model, "PhiStudy_bin"
        ),
    }


def projection(sample, observable, icat, ieta, n_eta, name):
    h2 = sample["h2_raw"].GetValue() if observable == "pt" else sample["h2_puppi"].GetValue()
    ybin = icat * n_eta + ieta + 1
    h = h2.ProjectionX(name, ybin, ybin, "e")
    h.SetDirectory(0)
    return h


def prepared(hist, name, counts):
    h = hist.Clone(name)
    h.SetDirectory(0)
    if not counts:
        integral = h.Integral(1, h.GetNbinsX())
        if integral > 0:
            h.Scale(1.0 / integral)
    return h


def min_positive(hists):
    out = None
    for h in hists:
        for i in range(1, h.GetNbinsX() + 1):
            v = h.GetBinContent(i)
            if v > 0 and (out is None or v < out):
                out = v
    return 1e-6 if out is None else max(out * 0.5, 1e-8)


def draw_file_overlay(samples, edges, category, ieta, observable, args, outdir, logy):
    n_eta = len(edges) - 1
    icat = CATEGORY_NAMES.index(category)

    hs = []
    for i, sample in enumerate(samples):
        h = projection(
            sample, observable, icat, ieta, n_eta,
            f"proj_{observable}_{icat}_{ieta}_{i}_{int(logy)}",
        )
        hs.append((
            sample,
            prepared(
                h,
                f"draw_{observable}_{icat}_{ieta}_{i}_{int(logy)}",
                args.counts,
            ),
        ))

    if not any(h.Integral() > 0 for _, h in hs):
        return False

    c = ROOT.TCanvas(f"c_{observable}_{icat}_{ieta}_{int(logy)}", "", 760, 600)
    c.SetTicks(1, 1)
    if logy:
        c.SetLogy()

    colors = [
        ROOT.kBlack, ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 2,
        ROOT.kMagenta + 1, ROOT.kOrange + 7, ROOT.kCyan + 2, ROOT.kViolet,
    ]

    ymax = max(h.GetMaximum() for _, h in hs)
    ymin = min_positive([h for _, h in hs]) if logy else 0.0

    leg = ROOT.TLegend(0.60, 0.68, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True
    for i, (sample, h) in enumerate(hs):
        h.SetStats(False)
        h.SetLineWidth(2)
        h.SetLineColor(colors[i % len(colors)])
        h.GetXaxis().SetTitle(
            "PF candidate p_{T} [GeV]"
            if observable == "pt"
            else "w_{PUPPI} #times p_{T} [GeV]"
        )
        h.GetYaxis().SetTitle(
            "Candidates" if args.counts else "Fraction of candidates / bin"
        )
        h.SetMinimum(ymin)
        h.SetMaximum(ymax * (20.0 if logy else 1.35))
        h.Draw("hist" if first else "hist same")
        first = False
        leg.AddEntry(h, f"{sample['label']} (N={int(h.GetEntries())})", "l")

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"
    if args.all_events:
        mode = "all events"
    elif args.min_nvtx is None:
        mode = f"event {args.event}"
    else:
        selected = ", ".join(
            f"{s['label']}: entry {s['selected_event']} (N_{{vtx}}={s['selected_nvtx']:g})"
            for s in samples
        )
        mode = selected
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.DrawLatex(
        0.13, 0.93,
        f"{CATEGORY_LABELS[category]}, {edges[ieta]:g} < {eta_symbol} < {edges[ieta+1]:g}"
    )
    latex.SetTextSize(0.030)
    latex.DrawLatex(0.13, 0.885, mode)

    tag = "pt" if observable == "pt" else "puppiPt"
    suffix = "log" if logy else "linear"
    c.SaveAs(str(outdir / f"overlay_{tag}_{category}_eta{ieta:02d}_{suffix}.png"))
    c.Close()
    return True



def draw_nvtx_overlay(samples, args, outdir, logy=False):
    """Overlay the event-level Nvtx distribution from all input files.

    In single-event mode, also draw a vertical line at the Nvtx value of the
    event actually selected for the PFCand study.
    """
    hs = []
    for i, sample in enumerate(samples):
        hsrc = sample["h_nvtx"].GetValue()
        h = prepared(hsrc, f"nvtx_draw_{i}_{int(logy)}", args.counts)
        hs.append((sample, h))

    if not any(h.Integral() > 0 for _, h in hs):
        return False

    c = ROOT.TCanvas(f"c_nvtx_{int(logy)}", "", 760, 600)
    c.SetTicks(1, 1)
    if logy:
        c.SetLogy()

    colors = [
        ROOT.kBlack, ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 2,
        ROOT.kMagenta + 1, ROOT.kOrange + 7, ROOT.kCyan + 2, ROOT.kViolet,
    ]

    ymax = max(h.GetMaximum() for _, h in hs)
    ymin = min_positive([h for _, h in hs]) if logy else 0.0

    leg = ROOT.TLegend(0.56, 0.64, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True
    selected_lines = []
    for i, (sample, h) in enumerate(hs):
        color = colors[i % len(colors)]
        h.SetStats(False)
        h.SetLineWidth(2)
        h.SetLineColor(color)
        h.GetXaxis().SetTitle("N_{vtx}")
        h.GetYaxis().SetTitle(
            "Events" if args.counts else "Fraction of events / bin"
        )
        h.SetMinimum(ymin)
        h.SetMaximum(ymax * (20.0 if logy else 1.35))
        h.Draw("hist" if first else "hist same")
        first = False

        leg.AddEntry(h, sample["label"], "l")

        if not args.all_events and sample["selected_nvtx"] is not None:
            line = ROOT.TLine(
                sample["selected_nvtx"],
                ymin if logy else 0.0,
                sample["selected_nvtx"],
                ymax * (10.0 if logy else 1.12),
            )
            line.SetLineColor(color)
            line.SetLineStyle(2)
            line.SetLineWidth(2)
            line.Draw("same")
            selected_lines.append(line)
            leg.AddEntry(
                line,
                f"{sample['label']} selected: N_{{vtx}}={sample['selected_nvtx']:g}",
                "l",
            )

    leg.Draw()

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.036)
    latex.DrawLatex(0.13, 0.93, "Vertex multiplicity")
    latex.SetTextSize(0.029)
    if args.all_events:
        latex.DrawLatex(0.13, 0.885, "event distribution used in the input sample")
    elif args.min_nvtx is None:
        latex.DrawLatex(0.13, 0.885, f"PFCand study uses entry {args.event}")
    else:
        latex.DrawLatex(
            0.13,
            0.885,
            f"selected from entry #geq {args.event} with N_{{vtx}} > {args.min_nvtx:g}",
        )

    suffix = "log" if logy else "linear"
    c.SaveAs(str(outdir / f"nvtx_overlay_{suffix}.png"))
    c.Close()
    return True


def category_multiplicity_hist(sample, edges, ieta, name):
    """Return one TH1D with category counts for a single eta ring."""
    n_eta = len(edges) - 1
    source = sample["h_category_eta_multiplicity"].GetValue()

    h = ROOT.TH1D(name, "", len(CATEGORY_NAMES), -0.5, len(CATEGORY_NAMES) - 0.5)
    h.SetDirectory(0)
    h.Sumw2(False)

    for icat, category in enumerate(CATEGORY_NAMES):
        combined = icat * n_eta + ieta
        source_bin = combined + 1
        count = source.GetBinContent(source_bin)
        h.SetBinContent(icat + 1, count)
        h.GetXaxis().SetBinLabel(icat + 1, category)

    return h


def draw_category_multiplicity_overlay(samples, edges, ieta, args, outdir, logy=False):
    """Overlay per-event PFCand counts by PF category for one eta ring."""
    hs = []
    for isample, sample in enumerate(samples):
        h = category_multiplicity_hist(
            sample,
            edges,
            ieta,
            f"h_mult_{isample}_{ieta}_{int(logy)}",
        )
        hs.append((sample, h))

    if not any(h.Integral() > 0 for _, h in hs):
        return False

    c = ROOT.TCanvas(f"c_mult_{ieta}_{int(logy)}", "", 880, 620)
    c.SetTicks(1, 1)
    c.SetBottomMargin(0.18)
    if logy:
        c.SetLogy()

    colors = [
        ROOT.kBlack, ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 2,
        ROOT.kMagenta + 1, ROOT.kOrange + 7, ROOT.kCyan + 2, ROOT.kViolet,
    ]
    markers = [20, 21, 22, 23, 24, 25, 26, 32]

    ymax = max(h.GetMaximum() for _, h in hs)
    ymin = min_positive([h for _, h in hs]) if logy else 0.0

    leg = ROOT.TLegend(0.65, 0.70, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True
    for i, (sample, h) in enumerate(hs):
        color = colors[i % len(colors)]
        h.SetStats(False)
        h.SetLineColor(color)
        h.SetMarkerColor(color)
        h.SetMarkerStyle(markers[i % len(markers)])
        h.SetMarkerSize(1.1)
        h.SetLineWidth(2)
        h.GetYaxis().SetTitle("PFCandidates")
        h.GetXaxis().LabelsOption("v")
        h.SetMinimum(ymin)
        h.SetMaximum(ymax * (20.0 if logy else 1.35))
        h.Draw("hist p" if first else "hist p same")
        first = False
        leg.AddEntry(h, sample["label"], "lp")

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.036)
    latex.DrawLatex(
        0.13,
        0.93,
        f"PFCandidate multiplicity, {edges[ieta]:g} < {eta_symbol} < {edges[ieta+1]:g}",
    )
    latex.SetTextSize(0.029)

    if args.all_events:
        mode = "all selected events (aggregate candidate counts)"
    elif args.min_nvtx is None:
        mode = f"entry {args.event}"
    else:
        mode = (
            f"first entry #geq {args.event} with N_{{vtx}} > {args.min_nvtx:g}"
        )
    latex.DrawLatex(0.13, 0.885, mode)

    suffix = "log" if logy else "linear"
    c.SaveAs(str(outdir / f"category_multiplicity_eta{ieta:02d}_{suffix}.png"))
    c.Close()
    return True


def write_category_multiplicity_csv(samples, edges, args, outdir):
    """Write exact per-category counts for every eta ring."""
    path = outdir / "category_multiplicity.csv"
    rows = []
    n_eta = len(edges) - 1

    for isample, sample in enumerate(samples):
        source = sample["h_category_eta_multiplicity"].GetValue()

        for ieta in range(n_eta):
            for icat, category in enumerate(CATEGORY_NAMES):
                combined = icat * n_eta + ieta
                count = int(round(source.GetBinContent(combined + 1)))

                rows.append({
                    "file": sample["filename"],
                    "label": sample["label"],
                    "event": "all" if args.all_events else sample["selected_event"],
                    "nvtx": "" if args.all_events else sample["selected_nvtx"],
                    "eta_min": edges[ieta],
                    "eta_max": edges[ieta + 1],
                    "category": category,
                    "count": count,
                })

    with path.open("w", newline="") as f:
        fields = [
            "file", "label", "event", "nvtx",
            "eta_min", "eta_max", "category", "count",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return path


def print_selected_event_multiplicities(samples, edges, args):
    """Compact terminal table for the selected event(s)."""
    if args.all_events:
        return

    n_eta = len(edges) - 1

    for sample in samples:
        source = sample["h_category_eta_multiplicity"].GetValue()
        print()
        print(
            f"{sample['label']}: entry {sample['selected_event']}, "
            f"{sample['nvtx_branch']}={sample['selected_nvtx']:g}"
        )

        for ieta in range(n_eta):
            counts = []
            total = 0
            for icat, category in enumerate(CATEGORY_NAMES):
                combined = icat * n_eta + ieta
                count = int(round(source.GetBinContent(combined + 1)))
                counts.append((category, count))
                total += count

            print(
                f"  eta [{edges[ieta]:g}, {edges[ieta+1]:g}): "
                f"total={total}"
            )
            print(
                "    " + ", ".join(
                    f"{category}={count}" for category, count in counts
                )
            )

def draw_raw_vs_puppi(sample, edges, category, ieta, args, outdir, isample, logy):
    n_eta = len(edges) - 1
    icat = CATEGORY_NAMES.index(category)

    raw = prepared(
        projection(sample, "pt", icat, ieta, n_eta, f"raw_{isample}_{icat}_{ieta}_{int(logy)}"),
        f"rawdraw_{isample}_{icat}_{ieta}_{int(logy)}",
        args.counts,
    )
    pup = prepared(
        projection(sample, "puppi_pt", icat, ieta, n_eta, f"pup_{isample}_{icat}_{ieta}_{int(logy)}"),
        f"pupdraw_{isample}_{icat}_{ieta}_{int(logy)}",
        args.counts,
    )

    if raw.Integral() <= 0 and pup.Integral() <= 0:
        return False

    c = ROOT.TCanvas(f"ccmp_{isample}_{icat}_{ieta}_{int(logy)}", "", 760, 600)
    c.SetTicks(1, 1)
    if logy:
        c.SetLogy()

    raw.SetStats(False)
    pup.SetStats(False)
    raw.SetLineWidth(2)
    pup.SetLineWidth(2)
    raw.SetLineColor(ROOT.kBlack)
    pup.SetLineColor(ROOT.kBlue + 1)

    raw.GetXaxis().SetTitle("p_{T}-like observable [GeV]")
    raw.GetYaxis().SetTitle(
        "Candidates" if args.counts else "Fraction of candidates / bin"
    )
    ymax = max(raw.GetMaximum(), pup.GetMaximum())
    raw.SetMaximum(ymax * (20.0 if logy else 1.35))
    raw.SetMinimum(min_positive([raw, pup]) if logy else 0.0)

    raw.Draw("hist")
    pup.Draw("hist same")

    leg = ROOT.TLegend(0.59, 0.73, 0.89, 0.88)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.AddEntry(raw, "raw p_{T}", "l")
    leg.AddEntry(pup, "w_{PUPPI} #times p_{T}", "l")
    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.DrawLatex(0.13, 0.93, f"{sample['label']}: {CATEGORY_LABELS[category]}")
    latex.SetTextSize(0.030)
    latex.DrawLatex(
        0.13, 0.885,
        f"{edges[ieta]:g} < {eta_symbol} < {edges[ieta+1]:g}"
    )

    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in sample["label"])
    suffix = "log" if logy else "linear"
    c.SaveAs(str(outdir / f"raw_vs_puppi_{safe}_{category}_eta{ieta:02d}_{suffix}.png"))
    c.Close()
    return True


def hist_quantiles(h):
    probs = array("d", [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    vals = array("d", [0.0] * len(probs))
    if h.Integral() > 0:
        h.GetQuantiles(len(probs), vals, probs)
    keys = ["q10", "q25", "median", "q75", "q90", "q95", "q99"]
    return {k: float(v) for k, v in zip(keys, vals)}


def write_summary(samples, edges, args, outdir):
    rows = []
    n_eta = len(edges) - 1

    for isample, sample in enumerate(samples):
        for category in args.categories:
            icat = CATEGORY_NAMES.index(category)
            for ieta in range(n_eta):
                for observable in ("pt", "puppi_pt"):
                    h = projection(
                        sample, observable, icat, ieta, n_eta,
                        f"sum_{isample}_{icat}_{ieta}_{observable}"
                    )
                    rows.append({
                        "file": sample["filename"],
                        "label": sample["label"],
                        "event": "all" if args.all_events else sample["selected_event"],
                        "nvtx": "" if args.all_events else sample["selected_nvtx"],
                        "nvtx_branch": sample["nvtx_branch"],
                        "observable": observable,
                        "category": category,
                        "eta_min": edges[ieta],
                        "eta_max": edges[ieta + 1],
                        "entries": int(h.GetEntries()),
                        "mean": float(h.GetMean()) if h.GetEntries() else float("nan"),
                        "stddev": float(h.GetStdDev()) if h.GetEntries() else float("nan"),
                        **hist_quantiles(h),
                    })

    path = outdir / "summary.csv"
    fields = [
        "file", "label", "event", "nvtx", "nvtx_branch", "observable", "category",
        "eta_min", "eta_max", "entries", "mean", "stddev",
        "q10", "q25", "median", "q75", "q90", "q95", "q99",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def main():
    args = parse_args()
    edges = validate(args)

    ROOT.gROOT.SetBatch(True)
    ROOT.TH1.AddDirectory(False)

    # Range is exact and single-threaded. Only unrestricted all-event mode uses IMT.
    if args.all_events and args.max_events < 0:
        if args.threads == 0:
            ROOT.EnableImplicitMT()
        elif args.threads > 1:
            ROOT.EnableImplicitMT(args.threads)

    declare_helpers()

    labels = args.labels or [Path(x).stem for x in args.inputs]

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    overlay_dir = outdir / "file_overlays"
    overlay_dir.mkdir(exist_ok=True)

    compare_dir = outdir / "raw_vs_puppi"
    if args.raw_vs_puppi:
        compare_dir.mkdir(exist_ok=True)

    multiplicity_dir = outdir / "category_multiplicity"
    multiplicity_dir.mkdir(exist_ok=True)

    # Create one subfolder per PF particle category.
    category_overlay_dirs = {}
    category_compare_dirs = {}

    for category in CATEGORY_NAMES:
        category_overlay_dirs[category] = overlay_dir / category
        category_overlay_dirs[category].mkdir(parents=True, exist_ok=True)

        if args.raw_vs_puppi:
            category_compare_dirs[category] = compare_dir / category
            category_compare_dirs[category].mkdir(parents=True, exist_ok=True)

    print("Particle classification:")
    print("  charged: e/mu by PID, otherwise chargedHadron")
    print("  neutral: photon/HF by PID, otherwise neutralHadron")
    print()
    print("Booking RDF graphs...")
    samples = []
    for i, (filename, label) in enumerate(zip(args.inputs, labels)):
        sample = make_sample(filename, label, args, edges, i)
        samples.append(sample)
        if args.all_events:
            mode = "all events"
        else:
            mode = (
                f"entry {sample['selected_event']} "
                f"({sample['nvtx_branch']}={sample['selected_nvtx']:g})"
            )
        print(
            f"  {label}: {mode}, PUPPI branch = {sample['weight']}, "
            f"Nvtx branch = {sample['nvtx_branch']}"
        )

    print("Running RDF graphs...")
    for sample in progress(samples, len(samples), "RDataFrame"):
        # Both histograms belong to the same graph, so the first GetValue()
        # triggers one event loop that fills both booked actions.
        sample["h2_raw"].GetValue()
        sample["h2_puppi"].GetValue()
        sample["h_category_eta_multiplicity"].GetValue()
        sample["h_nvtx"].GetValue()

    if args.save_root:
        f = ROOT.TFile.Open(str(outdir / "histograms.root"), "RECREATE")
        for i, sample in enumerate(samples):
            sample["h2_raw"].GetValue().Clone(f"raw_{i}").Write()
            sample["h2_puppi"].GetValue().Clone(f"puppiPt_{i}").Write()
            sample["h_category_eta_multiplicity"].GetValue().Clone(
                f"categoryEtaMultiplicity_{i}"
            ).Write()
            sample["h_nvtx"].GetValue().Clone(f"nvtx_{i}").Write()
        f.Close()

    print("Drawing Nvtx distribution...")
    made = 0
    made += int(draw_nvtx_overlay(samples, args, outdir, False))
    if not args.linear_only:
        made += int(draw_nvtx_overlay(samples, args, outdir, True))

    print("Drawing category multiplicities...")
    for ieta in progress(
        range(len(edges) - 1),
        len(edges) - 1,
        "Multiplicity",
    ):
        made += int(
            draw_category_multiplicity_overlay(
                samples, edges, ieta, args, multiplicity_dir, False
            )
        )
        if not args.linear_only:
            made += int(
                draw_category_multiplicity_overlay(
                    samples, edges, ieta, args, multiplicity_dir, True
                )
            )

    multiplicity_csv = write_category_multiplicity_csv(
        samples, edges, args, outdir
    )
    print_selected_event_multiplicities(samples, edges, args)

    jobs = []
    n_eta = len(edges) - 1
    for category in args.categories:
        for ieta in range(n_eta):
            for observable in ("pt", "puppi_pt"):
                jobs.append(("overlay", category, ieta, observable, False))
                if not args.linear_only:
                    jobs.append(("overlay", category, ieta, observable, True))

            if args.raw_vs_puppi:
                for isample in range(len(samples)):
                    jobs.append(("compare", category, ieta, isample, False))
                    if not args.linear_only:
                        jobs.append(("compare", category, ieta, isample, True))

    print("Drawing plots...")
    for job in progress(jobs, len(jobs), "Plots"):
        if job[0] == "overlay":
            _, category, ieta, observable, logy = job
            made += int(draw_file_overlay(
                samples, edges, category, ieta, observable,
                args, category_overlay_dirs[category], logy
            ))
        else:
            _, category, ieta, isample, logy = job
            made += int(draw_raw_vs_puppi(
                samples[isample], edges, category, ieta,
                args, category_compare_dirs[category], isample, logy
            ))

    summary = write_summary(samples, edges, args, outdir)

    print()
    print(f"Created {made} plots")
    print(f"Output: {outdir}")
    print(f"Summary: {summary}")
    print(f"Multiplicity CSV: {multiplicity_csv}")
    print("Particle-category subfolders:")
    for category in CATEGORY_NAMES:
        print(f"  file_overlays/{category}/")
        if args.raw_vs_puppi:
            print(f"  raw_vs_puppi/{category}/")
    if not args.all_events:
        if args.min_nvtx is None:
            print(f"Mode: exactly one event per file, entry {args.event}")
        else:
            print(
                f"Mode: first event at/after entry {args.event} with "
                f"Nvtx > {args.min_nvtx:g}"
            )
            for sample in samples:
                print(
                    f"  {sample['label']}: entry {sample['selected_event']}, "
                    f"{sample['nvtx_branch']}={sample['selected_nvtx']:g}"
                )


if __name__ == "__main__":
    main()
