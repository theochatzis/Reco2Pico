#!/usr/bin/env python3
"""
Direct phi-ring pileup-offset study with isolated charged hadrons.

For each selected event and eta ring, define

    deltaPt = E_T^calo,corr - responseScale * pT_track

with

    E_T^calo = E_calo / cosh(eta)

and, by default,

    responseScale = 1.

The charged-hadron PF calibration is therefore trusted by default rather than
refitted inside each event.  The ring offset is estimated from the robust
median of deltaPt after iterative rejection of only the large POSITIVE tail:

    deltaPt > median(deltaPt) + Nsigma * 1.4826 * MAD(deltaPt)

This protects the estimator from charged probes that pick up hard overlapping
calorimeter activity while preserving the lower side of the response
distribution.

The script also makes E_T^calo / pT_track validation plots.  These are intended
to test whether responseScale=1 is adequate as a function of eta and pT.

Default behaviour
-----------------
  * exactly one selected event per input file
  * charged non-leptonic PFCands
  * require isIsolatedChargedHadron == true
  * use corrected caloFraction/hcalFraction
  * pT_track in [3,20] GeV
  * estimate one offset per eta ring using the full phi range

Examples
--------
First event with Nvtx > 40:

  python3 pfcand_charged_offset_rings_direct.py ZeroBias.root \
      --label ZeroBias \
      --event 0 \
      --min-nvtx 40

Compare files:

  python3 pfcand_charged_offset_rings_direct.py data.root mc.root \
      --labels Data MC \
      --event 0 \
      --min-nvtx 40

Use a pre-measured response scale instead of 1:

  python3 pfcand_charged_offset_rings_direct.py pico.root \
      --response-scale 0.98

Cross-check all charged hadrons rather than only isolated ones:

  python3 pfcand_charged_offset_rings_direct.py pico.root \
      --probe-mode charged
"""

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ROOT

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, total=None, desc=None, **kwargs):
        if iterable is not None:
            return iterable

        class _Dummy:
            def update(self, n=1):
                pass
            def close(self):
                pass

        return _Dummy()


DEFAULT_ETA_BINS = [-3.0, -2.5, -1.5, 0.0, 1.5, 2.5, 3.0]

NVTX_CANDIDATES = [
    "PV_npvs",
    "PV_npvsGood",
    "nPV",
    "nPVGood",
    "nVertex",
    "nVertices",
]


@dataclass
class OffsetResult:
    valid: bool = False

    n_total: int = 0
    n_used: int = 0
    n_rejected: int = 0

    offset: float = float("nan")
    offset_error: float = float("nan")
    sigma: float = float("nan")

    response_median: float = float("nan")
    response_mean: float = float("nan")

    median_calo_et: float = float("nan")
    median_ecal_et: float = float("nan")
    median_hcal_et: float = float("nan")
    median_track_pt: float = float("nan")

    used_mask: np.ndarray = None


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Estimate an event-by-event eta-ring calorimeter offset from "
            "isolated charged hadrons using corrected calo energy minus track pT."
        )
    )

    p.add_argument("inputs", nargs="+", help="Input Pico ROOT files")

    p.add_argument("--label", default=None, help="Label for one input file")
    p.add_argument("--labels", nargs="+", default=None, help="One label per input")

    p.add_argument("--tree", default="Events")
    p.add_argument("--collection", default="PFCand")

    p.add_argument(
        "--event",
        type=int,
        default=0,
        help=(
            "Starting entry. Without --min-nvtx, use this exact event. "
            "With --min-nvtx, scan forward from here."
        ),
    )
    p.add_argument(
        "--min-nvtx",
        type=float,
        default=None,
        help="Select first event at/after --event with Nvtx > X.",
    )
    p.add_argument(
        "--nvtx-branch",
        default=None,
        help="Explicit Nvtx branch; otherwise common names are auto-detected.",
    )
    p.add_argument(
        "--all-events",
        action="store_true",
        help=(
            "Process all events at/after --event. In this mode --min-nvtx "
            "filters every event instead of selecting only the first passing event."
        ),
    )
    p.add_argument(
        "--max-events",
        type=int,
        default=-1,
        help="Maximum raw entries considered in --all-events mode; -1 = all.",
    )

    p.add_argument(
        "--eta-bins",
        nargs="+",
        type=float,
        default=DEFAULT_ETA_BINS,
    )
    p.add_argument(
        "--absolute-eta",
        action="store_true",
        help="Use |eta| rings. Eta edges must then be non-negative.",
    )

    p.add_argument(
        "--probe-mode",
        choices=["isolated", "charged"],
        default="charged",
        help=(
            "'isolated' requires PFCand_isIsolatedChargedHadron; "
            "'charged' uses all charged non-electron/non-muon candidates."
        ),
    )

    p.add_argument(
        "--energy-source",
        choices=["corrected", "raw"],
        default="raw",
        help=(
            "Corrected MiniAOD calorimeter fractions are the default. "
            "Use raw only as a cross-check."
        ),
    )

    p.add_argument(
        "--response-scale",
        type=float,
        default=1.0,
        help=(
            "Reference charged-hadron response R in "
            "deltaPt = caloEt - R*trackPt. Default: 1."
        ),
    )

    p.add_argument("--probe-pt-min", type=float, default=0.0)
    p.add_argument("--probe-pt-max", type=float, default=5.0)
    p.add_argument(
        "--offset-pt-bins",
        nargs="+",
        type=float,
        default=None,
        help=(
            "Track-pT edges for all-event offset studies. If omitted, "
            "soft-PF-oriented bins are generated inside the probe pT range."
        ),
    )
    p.add_argument("--nvtx-plot-min", type=float, default=0.0)
    p.add_argument("--nvtx-plot-max", type=float, default=80.0)
    p.add_argument("--nvtx-plot-bins", type=int, default=16)
    p.add_argument("--offset-hist-bins", type=int, default=80)
    p.add_argument(
        "--min-events-per-average",
        type=int,
        default=5,
        help="Minimum valid event offsets required to draw an average point.",
    )

    p.add_argument(
        "--min-probes",
        type=int,
        default=8,
        help="Minimum accepted probes needed to quote an offset.",
    )
    p.add_argument(
        "--n-sigma",
        type=float,
        default=3.0,
        help="One-sided positive-tail clipping threshold in robust sigma.",
    )
    p.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Maximum robust clipping iterations.",
    )

    p.add_argument(
        "--delta-pt-range",
        type=float,
        default=5.0,
        help="Absolute deltaPt plotting range in GeV.",
    )
    p.add_argument(
        "--ratio-max",
        type=float,
        default=2.0,
        help="Maximum E_T^calo / pT_track shown in response histograms.",
    )

    p.add_argument(
        "--linear-only",
        action="store_true",
        help="Skip log-y versions of histograms.",
    )

    p.add_argument(
        "--output-dir",
        default="charged_hadron_phi_offset_direct",
    )

    p.add_argument(
        "--save-root",
        action="store_true",
        help="Save eta summary histograms to offsetStudy.root.",
    )

    return p.parse_args()


def validate_args(args):
    if args.event < 0:
        raise ValueError("--event must be >= 0")

    if args.probe_pt_max <= args.probe_pt_min:
        raise ValueError("--probe-pt-max must be > --probe-pt-min")

    if args.min_probes < 1:
        raise ValueError("--min-probes must be > 0")

    if args.n_sigma <= 0:
        raise ValueError("--n-sigma must be > 0")

    if args.response_scale <= 0:
        raise ValueError("--response-scale must be > 0")

    if args.max_events == 0 or args.max_events < -1:
        raise ValueError("--max-events must be -1 or positive")

    if args.nvtx_plot_max <= args.nvtx_plot_min:
        raise ValueError("--nvtx-plot-max must be > --nvtx-plot-min")

    if args.nvtx_plot_bins <= 0 or args.offset_hist_bins <= 0:
        raise ValueError("Histogram bin counts must be positive")

    if args.min_events_per_average < 1:
        raise ValueError("--min-events-per-average must be positive")

    edges = np.asarray(args.eta_bins, dtype=float)

    if len(edges) < 2 or np.any(np.diff(edges) <= 0):
        raise ValueError("--eta-bins must be strictly increasing")

    if args.absolute_eta and np.any(edges < 0):
        raise ValueError("--absolute-eta requires non-negative eta-bin edges")

    if args.label is not None and len(args.inputs) != 1:
        raise ValueError("--label can only be used with one input file")

    if args.labels is not None and len(args.labels) != len(args.inputs):
        raise ValueError("--labels must contain exactly one label per input file")

    if args.offset_pt_bins is not None:
        ptedges = np.asarray(args.offset_pt_bins, dtype=float)
        if len(ptedges) < 2 or np.any(np.diff(ptedges) <= 0):
            raise ValueError("--offset-pt-bins must be strictly increasing")
        if ptedges[0] < args.probe_pt_min or ptedges[-1] > args.probe_pt_max:
            raise ValueError(
                "--offset-pt-bins must lie inside the probe pT range"
            )

    return edges


def labels_for(args):
    if args.labels is not None:
        return args.labels

    if args.label is not None:
        return [args.label]

    return [Path(x).stem for x in args.inputs]


def tree_info(filename, tree_name):
    f = ROOT.TFile.Open(filename)

    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open {filename}")

    tree = f.Get(tree_name)

    if not tree:
        f.Close()
        raise RuntimeError(f"{filename}: tree '{tree_name}' not found")

    branches = {b.GetName() for b in tree.GetListOfBranches()}
    entries = int(tree.GetEntries())

    f.Close()

    return branches, entries


def scalar_branch_value(tree, branch_name):
    """
    Read scalar values through TLeaf.

    This avoids the PyROOT UChar_t issue where a number can appear as a
    one-character Python string.
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
            f"Could not obtain scalar TLeaf for branch '{branch_name}'"
        )

    return float(leaf.GetValue(0))


def detect_nvtx_branch(branches, explicit):
    if explicit is not None:
        if explicit not in branches:
            raise RuntimeError(f"Nvtx branch '{explicit}' was not found")

        return explicit

    for name in NVTX_CANDIDATES:
        if name in branches:
            return name

    return None


def choose_event(filename, args, nvtx_branch):
    _, entries = tree_info(filename, args.tree)

    if args.event >= entries:
        raise RuntimeError(
            f"{filename}: entry {args.event} requested, "
            f"but the file contains only {entries} entries"
        )

    f = ROOT.TFile.Open(filename)
    tree = f.Get(args.tree)

    if args.min_nvtx is None:
        selected = args.event

        tree.GetEntry(selected)

        nvtx = (
            scalar_branch_value(tree, nvtx_branch)
            if nvtx_branch is not None
            else float("nan")
        )

        f.Close()

        return selected, nvtx

    if nvtx_branch is None:
        f.Close()

        raise RuntimeError(
            f"{filename}: --min-nvtx requested but no Nvtx branch was found"
        )

    for entry in range(args.event, entries):
        tree.GetEntry(entry)

        nvtx = scalar_branch_value(tree, nvtx_branch)

        if nvtx > args.min_nvtx:
            f.Close()

            return entry, nvtx

    f.Close()

    raise RuntimeError(
        f"{filename}: no event at/after entry {args.event} satisfies "
        f"{nvtx_branch} > {args.min_nvtx}"
    )


def vector_to_numpy(value, dtype=float):
    if isinstance(value, np.ndarray) and value.dtype != object:
        return np.asarray(value, dtype=dtype)

    try:
        return np.asarray(list(value), dtype=dtype)
    except TypeError:
        return np.asarray(value, dtype=dtype)


def read_event(filename, label, args):
    branches, _ = tree_info(filename, args.tree)

    nvtx_branch = detect_nvtx_branch(branches, args.nvtx_branch)

    selected_entry, selected_nvtx = choose_event(
        filename,
        args,
        nvtx_branch,
    )

    prefix = args.collection

    names = {
        "pt": f"{prefix}_pt",
        "eta": f"{prefix}_eta",
        "phi": f"{prefix}_phi",
        "energy": f"{prefix}_energy",
        "pdgId": f"{prefix}_pdgId",
        "charge": f"{prefix}_charge",
        "ptTrk": f"{prefix}_ptTrk",
        "caloFraction": f"{prefix}_caloFraction",
        "hcalFraction": f"{prefix}_hcalFraction",
        "rawCaloFraction": f"{prefix}_rawCaloFraction",
        "rawHcalFraction": f"{prefix}_rawHcalFraction",
        "isolated": f"{prefix}_isIsolatedChargedHadron",
    }

    required_keys = [
        "pt",
        "eta",
        "phi",
        "energy",
        "pdgId",
        "charge",
        "ptTrk",
    ]

    if args.energy_source == "corrected":
        required_keys += ["caloFraction", "hcalFraction"]
    else:
        required_keys += ["rawCaloFraction", "rawHcalFraction"]

    if args.probe_mode == "isolated":
        required_keys += ["isolated"]

    missing = [
        names[key]
        for key in required_keys
        if names[key] not in branches
    ]

    if missing:
        raise RuntimeError(
            f"{filename}: missing required branches:\n  "
            + "\n  ".join(missing)
        )

    request = [names[key] for key in required_keys]

    # Avoid duplicates if a key is repeated above.
    request = list(dict.fromkeys(request))

    df = ROOT.RDataFrame(args.tree, filename).Range(
        selected_entry,
        selected_entry + 1,
    )

    arrays = df.AsNumpy(request)

    def get_vec(key, dtype=float):
        branch = names[key]

        if branch not in arrays:
            return None

        payload = arrays[branch]

        if len(payload) != 1:
            raise RuntimeError(
                f"{filename}: expected exactly one selected event for {branch}"
            )

        return vector_to_numpy(payload[0], dtype=dtype)

    data = {
        "pt": get_vec("pt"),
        "eta": get_vec("eta"),
        "phi": get_vec("phi"),
        "energy": get_vec("energy"),
        "pdgId": get_vec("pdgId", dtype=np.int32),
        "charge": get_vec("charge", dtype=np.int32),
        "ptTrk": get_vec("ptTrk"),
    }

    if args.energy_source == "corrected":
        data["caloFraction"] = get_vec("caloFraction")
        data["hcalFraction"] = get_vec("hcalFraction")
    else:
        data["caloFraction"] = get_vec("rawCaloFraction")
        data["hcalFraction"] = get_vec("rawHcalFraction")

    if args.probe_mode == "isolated":
        data["isolated"] = get_vec("isolated", dtype=np.int32)
    else:
        data["isolated"] = np.ones_like(data["charge"], dtype=np.int32)

    n = len(data["pt"])

    for key, values in data.items():
        if values is None:
            continue

        if len(values) != n:
            raise RuntimeError(
                f"{filename}: inconsistent PFCand vector length for {key}: "
                f"{len(values)} vs {n}"
            )

    apid = np.abs(data["pdgId"])

    probe_mask = (
        (data["charge"] != 0)
        & (apid != 11)
        & (apid != 13)
        & np.isfinite(data["ptTrk"])
        & (data["ptTrk"] >= args.probe_pt_min)
        & (data["ptTrk"] <= args.probe_pt_max)
        & (data["isolated"] != 0)
    )

    calo_fraction = data["caloFraction"]
    hcal_fraction = data["hcalFraction"]

    probe_mask &= (
        np.isfinite(calo_fraction)
        & np.isfinite(hcal_fraction)
        & (calo_fraction > 0)
    )

    calo_energy = data["energy"] * calo_fraction
    hcal_energy = calo_energy * hcal_fraction
    ecal_energy = calo_energy - hcal_energy

    cosh_eta = np.cosh(data["eta"])

    calo_et = np.divide(
        calo_energy,
        cosh_eta,
        out=np.zeros_like(calo_energy),
        where=cosh_eta > 0,
    )

    ecal_et = np.divide(
        ecal_energy,
        cosh_eta,
        out=np.zeros_like(ecal_energy),
        where=cosh_eta > 0,
    )

    hcal_et = np.divide(
        hcal_energy,
        cosh_eta,
        out=np.zeros_like(hcal_energy),
        where=cosh_eta > 0,
    )

    delta_pt = calo_et - args.response_scale * data["ptTrk"]

    response = np.divide(
        calo_et,
        data["ptTrk"],
        out=np.full_like(calo_et, np.nan),
        where=data["ptTrk"] > 0,
    )

    probe_mask &= (
        np.isfinite(calo_et)
        & np.isfinite(ecal_et)
        & np.isfinite(hcal_et)
        & np.isfinite(delta_pt)
        & np.isfinite(response)
    )

    eta_for_bins = (
        np.abs(data["eta"])
        if args.absolute_eta
        else data["eta"]
    )

    return {
        "filename": filename,
        "label": label,
        "entry": selected_entry,
        "nvtx": selected_nvtx,
        "nvtx_branch": nvtx_branch,
        "eta_for_bins": eta_for_bins,
        "probe_mask": probe_mask,
        "caloEt": calo_et,
        "ecalEt": ecal_et,
        "hcalEt": hcal_et,
        "deltaPt": delta_pt,
        "response": response,
        **data,
    }


def robust_sigma(values, center=None):
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return float("nan")

    if center is None:
        center = float(np.median(values))

    mad = float(np.median(np.abs(values - center)))

    return 1.4826 * mad


def estimate_offset(
    delta_pt,
    response,
    track_pt,
    calo_et,
    ecal_et,
    hcal_et,
    min_probes,
    n_sigma,
    max_iterations,
):
    result = OffsetResult()
    result.n_total = int(len(delta_pt))

    if len(delta_pt) < min_probes:
        return result

    used = np.ones(len(delta_pt), dtype=bool)

    for _ in range(max_iterations):
        values = delta_pt[used]

        if len(values) < min_probes:
            return result

        center = float(np.median(values))
        sigma = robust_sigma(values, center)

        if not np.isfinite(sigma) or sigma <= 0:
            break

        upper = center + n_sigma * sigma

        # Protect only against the positive tail.  Large positive values are
        # the natural signature of hard overlapping calorimeter activity.
        new_used = used & (delta_pt <= upper)

        if np.count_nonzero(new_used) < min_probes:
            return result

        if np.array_equal(new_used, used):
            used = new_used
            break

        used = new_used

    values = delta_pt[used]

    if len(values) < min_probes:
        return result

    offset = float(np.median(values))
    sigma = robust_sigma(values, offset)

    # Approximate standard error of a sample median for a Gaussian-like core.
    # This is diagnostic only; it is not intended as the final uncertainty model.
    offset_error = (
        1.253314 * sigma / math.sqrt(len(values))
        if np.isfinite(sigma)
        else float("nan")
    )

    response_values = response[used]

    result.valid = True

    result.n_used = int(np.count_nonzero(used))
    result.n_rejected = result.n_total - result.n_used

    result.offset = offset
    result.offset_error = offset_error
    result.sigma = sigma

    result.response_median = float(np.median(response_values))
    result.response_mean = float(np.mean(response_values))

    result.median_calo_et = float(np.median(calo_et[used]))
    result.median_ecal_et = float(np.median(ecal_et[used]))
    result.median_hcal_et = float(np.median(hcal_et[used]))
    result.median_track_pt = float(np.median(track_pt[used]))

    result.used_mask = used

    return result


def ring_payload(sample, eta_lo, eta_hi):
    mask = (
        sample["probe_mask"]
        & (sample["eta_for_bins"] >= eta_lo)
        & (sample["eta_for_bins"] < eta_hi)
    )

    idx = np.nonzero(mask)[0]

    return {
        "indices": idx,
        "phi": sample["phi"][idx],
        "eta": sample["eta"][idx],
        "trackPt": sample["ptTrk"][idx],
        "caloEt": sample["caloEt"][idx],
        "ecalEt": sample["ecalEt"][idx],
        "hcalEt": sample["hcalEt"][idx],
        "deltaPt": sample["deltaPt"][idx],
        "response": sample["response"][idx],
    }


def eta_tag(lo, hi):
    def one(x):
        return f"{x:+.2f}".replace("+", "p").replace("-", "m")

    return f"eta_{one(lo)}_{one(hi)}"


def make_hist(name, values, nbins, xmin, xmax):
    h = ROOT.TH1D(name, "", nbins, xmin, xmax)
    h.SetDirectory(0)

    for value in values:
        if np.isfinite(value):
            h.Fill(float(value))

    return h


def palette():
    return [
        ROOT.kBlack,
        ROOT.kRed + 1,
        ROOT.kBlue + 1,
        ROOT.kGreen + 2,
        ROOT.kMagenta + 1,
        ROOT.kOrange + 7,
        ROOT.kCyan + 2,
        ROOT.kViolet,
    ]


def draw_delta_hist(items, eta_lo, eta_hi, args, outdir, logy=False):
    available = [
        (sample, ring, result)
        for sample, ring, result in items
        if len(ring["deltaPt"]) > 0
    ]

    if not available:
        return False

    c = ROOT.TCanvas(
        f"c_delta_{eta_tag(eta_lo, eta_hi)}_{int(logy)}",
        "",
        790,
        610,
    )
    c.SetTicks(1, 1)

    if logy:
        c.SetLogy()

    colors = palette()

    hs = []
    ymax = 0.0

    for i, (sample, ring, result) in enumerate(available):
        values = (
            ring["deltaPt"][result.used_mask]
            if result.valid
            else ring["deltaPt"]
        )

        h = make_hist(
            f"h_delta_{i}_{eta_tag(eta_lo, eta_hi)}_{int(logy)}",
            values,
            70,
            -args.delta_pt_range,
            args.delta_pt_range,
        )

        if h.Integral() > 0:
            h.Scale(1.0 / h.Integral())

        h.SetStats(False)
        h.SetLineWidth(2)
        h.SetLineColor(colors[i % len(colors)])

        ymax = max(ymax, h.GetMaximum())

        hs.append((sample, result, h))

    if not hs:
        c.Close()

        return False

    leg = ROOT.TLegend(0.53, 0.66, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True

    for sample, result, h in hs:
        h.GetXaxis().SetTitle(
            "#Delta p_{T} = E_{T}^{calo,corr} - R p_{T}^{track} [GeV]"
        )
        h.GetYaxis().SetTitle("Fraction of probes / bin")
        h.SetMaximum(max(ymax * (30.0 if logy else 1.35), 1e-3))

        if logy:
            h.SetMinimum(1e-4)

        h.Draw("hist" if first else "hist same")
        first = False

        if result.valid:
            text = (
                f"{sample['label']}: O={result.offset:+.3f} GeV, "
                f"N={result.n_used}"
            )
        else:
            text = f"{sample['label']}: insufficient probes"

        leg.AddEntry(h, text, "l")

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"

    latex = ROOT.TLatex()
    latex.SetNDC()

    latex.SetTextSize(0.036)
    latex.DrawLatex(
        0.13,
        0.93,
        f"Charged-hadron offset: {eta_lo:g} < {eta_symbol} < {eta_hi:g}",
    )

    latex.SetTextSize(0.029)
    latex.DrawLatex(
        0.13,
        0.885,
        f"{args.energy_source} calo; response scale R={args.response_scale:g}",
    )

    suffix = "log" if logy else "linear"

    c.SaveAs(str(outdir / f"deltaPt_{suffix}.png"))
    c.Close()

    return True


def draw_delta_vs_phi(items, eta_lo, eta_hi, args, outdir):
    available = [
        (sample, ring, result)
        for sample, ring, result in items
        if result.valid
    ]

    if not available:
        return False

    c = ROOT.TCanvas(
        f"c_phi_{eta_tag(eta_lo, eta_hi)}",
        "",
        800,
        620,
    )
    c.SetTicks(1, 1)

    frame = ROOT.TH1D(
        f"frame_phi_{eta_tag(eta_lo, eta_hi)}",
        "",
        100,
        -math.pi,
        math.pi,
    )
    frame.SetDirectory(0)
    frame.SetStats(False)

    frame.GetXaxis().SetTitle("#phi")
    frame.GetYaxis().SetTitle(
        "#Delta p_{T} = E_{T}^{calo,corr} - R p_{T}^{track} [GeV]"
    )

    frame.SetMinimum(-args.delta_pt_range)
    frame.SetMaximum(args.delta_pt_range)

    frame.Draw()

    keep_alive = [frame]

    colors = palette()

    leg = ROOT.TLegend(0.60, 0.67, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for i, (sample, ring, result) in enumerate(available):
        color = colors[i % len(colors)]

        accepted = result.used_mask
        rejected = ~result.used_mask

        if np.any(accepted):
            g = ROOT.TGraph(
                int(np.count_nonzero(accepted)),
                ring["phi"][accepted].astype(np.float64),
                ring["deltaPt"][accepted].astype(np.float64),
            )

            g.SetMarkerStyle(20)
            g.SetMarkerSize(0.9)
            g.SetMarkerColor(color)
            g.Draw("P SAME")

            keep_alive.append(g)

            leg.AddEntry(g, f"{sample['label']} accepted", "p")

        if np.any(rejected):
            gr = ROOT.TGraph(
                int(np.count_nonzero(rejected)),
                ring["phi"][rejected].astype(np.float64),
                ring["deltaPt"][rejected].astype(np.float64),
            )

            gr.SetMarkerStyle(24)
            gr.SetMarkerSize(1.1)
            gr.SetMarkerColor(color)
            gr.Draw("P SAME")

            keep_alive.append(gr)

        line = ROOT.TLine(
            -math.pi,
            result.offset,
            math.pi,
            result.offset,
        )
        line.SetLineColor(color)
        line.SetLineWidth(2)
        line.SetLineStyle(2)
        line.Draw()

        keep_alive.append(line)

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"

    latex = ROOT.TLatex()
    latex.SetNDC()

    latex.SetTextSize(0.036)
    latex.DrawLatex(
        0.13,
        0.93,
        f"Offset probes around #phi: {eta_lo:g} < {eta_symbol} < {eta_hi:g}",
    )

    c.SaveAs(str(outdir / "deltaPt_vs_phi.png"))
    c.Close()

    return True


def draw_response_hist(items, eta_lo, eta_hi, args, outdir):
    available = [
        (sample, ring, result)
        for sample, ring, result in items
        if len(ring["response"]) > 0
    ]

    if not available:
        return False

    c = ROOT.TCanvas(
        f"c_response_{eta_tag(eta_lo, eta_hi)}",
        "",
        790,
        610,
    )
    c.SetTicks(1, 1)

    colors = palette()

    hs = []
    ymax = 0.0

    for i, (sample, ring, result) in enumerate(available):
        values = (
            ring["response"][result.used_mask]
            if result.valid
            else ring["response"]
        )

        h = make_hist(
            f"h_response_{i}_{eta_tag(eta_lo, eta_hi)}",
            values,
            70,
            0.0,
            args.ratio_max,
        )

        if h.Integral() > 0:
            h.Scale(1.0 / h.Integral())

        h.SetStats(False)
        h.SetLineWidth(2)
        h.SetLineColor(colors[i % len(colors)])

        ymax = max(ymax, h.GetMaximum())

        hs.append((sample, result, h))

    leg = ROOT.TLegend(0.58, 0.69, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True

    for sample, result, h in hs:
        h.GetXaxis().SetTitle("E_{T}^{calo,corr} / p_{T}^{track}")
        h.GetYaxis().SetTitle("Fraction of probes / bin")
        h.SetMaximum(max(ymax * 1.35, 1e-3))

        h.Draw("hist" if first else "hist same")
        first = False

        if result.valid:
            leg.AddEntry(
                h,
                f"{sample['label']}: median={result.response_median:.3f}",
                "l",
            )
        else:
            leg.AddEntry(h, sample["label"], "l")

    one = ROOT.TLine(
        args.response_scale,
        0.0,
        args.response_scale,
        max(ymax * 1.2, 1e-3),
    )
    one.SetLineStyle(2)
    one.SetLineWidth(2)
    one.Draw()

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.036)
    latex.DrawLatex(
        0.13,
        0.93,
        f"Charged-hadron response: {eta_lo:g} < {eta_symbol} < {eta_hi:g}",
    )

    c.SaveAs(str(outdir / "caloEt_over_trackPt.png"))
    c.Close()

    return True


def draw_calo_vs_track(items, eta_lo, eta_hi, args, outdir):
    available = [
        (sample, ring, result)
        for sample, ring, result in items
        if len(ring["trackPt"]) > 0
    ]

    if not available:
        return False

    c = ROOT.TCanvas(
        f"c_calo_track_{eta_tag(eta_lo, eta_hi)}",
        "",
        800,
        620,
    )
    c.SetTicks(1, 1)

    ymax = max(
        [
            float(np.max(ring["caloEt"]))
            for _, ring, _ in available
            if len(ring["caloEt"])
        ]
        + [args.probe_pt_max]
    )

    frame = ROOT.TH1D(
        f"frame_calo_track_{eta_tag(eta_lo, eta_hi)}",
        "",
        100,
        args.probe_pt_min,
        args.probe_pt_max,
    )
    frame.SetDirectory(0)
    frame.SetStats(False)

    frame.GetXaxis().SetTitle("p_{T}^{track} [GeV]")
    frame.GetYaxis().SetTitle("E_{T}^{calo,corr} [GeV]")

    frame.SetMinimum(0.0)
    frame.SetMaximum(ymax * 1.25)

    frame.Draw()

    keep_alive = [frame]
    colors = palette()

    leg = ROOT.TLegend(0.62, 0.70, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for i, (sample, ring, result) in enumerate(available):
        color = colors[i % len(colors)]

        g = ROOT.TGraph(
            len(ring["trackPt"]),
            ring["trackPt"].astype(np.float64),
            ring["caloEt"].astype(np.float64),
        )

        g.SetMarkerStyle(20 + (i % 5))
        g.SetMarkerSize(0.85)
        g.SetMarkerColor(color)
        g.Draw("P SAME")

        keep_alive.append(g)
        leg.AddEntry(g, sample["label"], "p")

    reference = ROOT.TF1(
        f"reference_{eta_tag(eta_lo, eta_hi)}",
        f"{args.response_scale}*x",
        args.probe_pt_min,
        args.probe_pt_max,
    )
    reference.SetLineColor(ROOT.kGray + 2)
    reference.SetLineStyle(2)
    reference.SetLineWidth(2)
    reference.Draw("SAME")

    keep_alive.append(reference)

    leg.AddEntry(
        reference,
        f"E_{{T}}^{{calo}}={args.response_scale:g} p_{{T}}^{{track}}",
        "l",
    )

    leg.Draw()

    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.036)
    latex.DrawLatex(
        0.13,
        0.93,
        f"Calo response validation: {eta_lo:g} < {eta_symbol} < {eta_hi:g}",
    )

    c.SaveAs(str(outdir / "caloEt_vs_trackPt.png"))
    c.Close()

    return True


def draw_calo_components(items, eta_lo, eta_hi, args, outdir):
    available = [
        (sample, ring, result)
        for sample, ring, result in items
        if result.valid
    ]

    if not available:
        return False

    # One plot per input file because overlaying ECAL/HCAL components from many
    # samples becomes hard to read.
    for isample, (sample, ring, result) in enumerate(available):
        used = result.used_mask

        values = {
            "ECAL": ring["ecalEt"][used],
            "HCAL": ring["hcalEt"][used],
            "ECAL+HCAL": ring["caloEt"][used],
        }

        xmax = max(
            [
                float(np.quantile(v, 0.99))
                for v in values.values()
                if len(v)
            ]
            + [1.0]
        )
        xmax = max(xmax * 1.2, 2.0)

        c = ROOT.TCanvas(
            f"c_components_{isample}_{eta_tag(eta_lo, eta_hi)}",
            "",
            790,
            610,
        )
        c.SetTicks(1, 1)

        component_colors = [
            ROOT.kRed + 1,
            ROOT.kBlue + 1,
            ROOT.kBlack,
        ]

        hs = []
        ymax = 0.0

        for i, (name, vals) in enumerate(values.items()):
            h = make_hist(
                f"h_component_{i}_{isample}_{eta_tag(eta_lo, eta_hi)}",
                vals,
                60,
                0.0,
                xmax,
            )

            if h.Integral() > 0:
                h.Scale(1.0 / h.Integral())

            h.SetStats(False)
            h.SetLineWidth(2)
            h.SetLineColor(component_colors[i])

            ymax = max(ymax, h.GetMaximum())

            hs.append((name, h))

        leg = ROOT.TLegend(0.64, 0.72, 0.89, 0.89)
        leg.SetBorderSize(0)
        leg.SetFillStyle(0)

        first = True

        for name, h in hs:
            h.GetXaxis().SetTitle("Calorimeter transverse energy [GeV]")
            h.GetYaxis().SetTitle("Fraction of accepted probes / bin")
            h.SetMaximum(max(ymax * 1.35, 1e-3))

            h.Draw("hist" if first else "hist same")
            first = False

            leg.AddEntry(h, name, "l")

        leg.Draw()

        latex = ROOT.TLatex()
        latex.SetNDC()
        latex.SetTextSize(0.036)
        latex.DrawLatex(
            0.13,
            0.93,
            f"{sample['label']}: accepted charged probes",
        )

        safe_label = "".join(
            ch if ch.isalnum() or ch in "._-" else "_"
            for ch in sample["label"]
        )

        c.SaveAs(str(outdir / f"calo_components_{safe_label}.png"))
        c.Close()

    return True


def summary_graph(
    samples,
    all_results,
    eta_edges,
    args,
    outdir,
    field,
    ylabel,
    filename,
    with_errors=False,
):
    centers = 0.5 * (eta_edges[:-1] + eta_edges[1:])

    values_all = []

    for sample in samples:
        for result in all_results[sample["label"]]:
            if not result.valid:
                continue

            value = getattr(result, field)

            if np.isfinite(value):
                values_all.append(float(value))

    if not values_all:
        return False

    c = ROOT.TCanvas(f"c_summary_{field}", "", 790, 610)
    c.SetTicks(1, 1)

    frame = ROOT.TH1D(
        f"frame_summary_{field}",
        "",
        100,
        float(eta_edges[0]),
        float(eta_edges[-1]),
    )
    frame.SetDirectory(0)
    frame.SetStats(False)

    frame.GetXaxis().SetTitle("|#eta|" if args.absolute_eta else "#eta")
    frame.GetYaxis().SetTitle(ylabel)

    lo = min(values_all)
    hi = max(values_all)

    if field in ("n_used", "n_rejected"):
        frame.SetMinimum(0.0)
        frame.SetMaximum(max(1.0, hi * 1.35))
    else:
        span = max(hi - lo, 0.1)
        frame.SetMinimum(lo - 0.30 * span)
        frame.SetMaximum(hi + 0.35 * span)

    frame.Draw()

    keep_alive = [frame]
    colors = palette()

    leg = ROOT.TLegend(0.64, 0.73, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for isample, sample in enumerate(samples):
        xs = []
        ys = []
        exs = []
        eys = []

        for center, result in zip(
            centers,
            all_results[sample["label"]],
        ):
            if not result.valid:
                continue

            value = getattr(result, field)

            if not np.isfinite(value):
                continue

            xs.append(center)
            ys.append(value)
            exs.append(0.0)

            if with_errors and np.isfinite(result.offset_error):
                eys.append(result.offset_error)
            else:
                eys.append(0.0)

        if not xs:
            continue

        graph = ROOT.TGraphErrors(
            len(xs),
            np.asarray(xs, dtype=np.float64),
            np.asarray(ys, dtype=np.float64),
            np.asarray(exs, dtype=np.float64),
            np.asarray(eys, dtype=np.float64),
        )

        graph.SetMarkerStyle(20 + (isample % 5))
        graph.SetMarkerSize(1.0)
        graph.SetMarkerColor(colors[isample % len(colors)])
        graph.SetLineColor(colors[isample % len(colors)])

        graph.Draw("P SAME")

        keep_alive.append(graph)
        leg.AddEntry(graph, sample["label"], "p")

    if field == "response_median":
        line = ROOT.TLine(
            float(eta_edges[0]),
            args.response_scale,
            float(eta_edges[-1]),
            args.response_scale,
        )
        line.SetLineStyle(2)
        line.SetLineWidth(2)
        line.SetLineColor(ROOT.kGray + 2)
        line.Draw()

        keep_alive.append(line)

    leg.Draw()

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.036)

    latex.DrawLatex(
        0.13,
        0.93,
        f"Isolated charged-hadron phi-ring study ({args.energy_source})",
    )

    c.SaveAs(str(outdir / filename))
    c.Close()

    return True


def write_csv(samples, all_results, eta_edges, args, outdir):
    path = outdir / "offset_summary.csv"

    fields = [
        "file",
        "label",
        "selected_entry",
        "nvtx_branch",
        "nvtx",
        "eta_min",
        "eta_max",
        "probe_mode",
        "energy_source",
        "response_scale",
        "n_total",
        "n_used",
        "n_rejected",
        "valid",
        "offset_GeV",
        "offset_error_approx_GeV",
        "robust_sigma_GeV",
        "response_median",
        "response_mean",
        "median_trackPt_GeV",
        "median_caloEt_GeV",
        "median_ecalEt_GeV",
        "median_hcalEt_GeV",
    ]

    rows = []

    for sample in samples:
        for ieta, result in enumerate(all_results[sample["label"]]):
            rows.append({
                "file": sample["filename"],
                "label": sample["label"],
                "selected_entry": sample["entry"],
                "nvtx_branch": sample["nvtx_branch"] or "",
                "nvtx": sample["nvtx"],
                "eta_min": eta_edges[ieta],
                "eta_max": eta_edges[ieta + 1],
                "probe_mode": args.probe_mode,
                "energy_source": args.energy_source,
                "response_scale": args.response_scale,
                "n_total": result.n_total,
                "n_used": result.n_used,
                "n_rejected": result.n_rejected,
                "valid": int(result.valid),
                "offset_GeV": result.offset,
                "offset_error_approx_GeV": result.offset_error,
                "robust_sigma_GeV": result.sigma,
                "response_median": result.response_median,
                "response_mean": result.response_mean,
                "median_trackPt_GeV": result.median_track_pt,
                "median_caloEt_GeV": result.median_calo_et,
                "median_ecalEt_GeV": result.median_ecal_et,
                "median_hcalEt_GeV": result.median_hcal_et,
            })

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return path


def save_root(samples, all_results, eta_edges, args, outdir):
    path = outdir / "offsetStudy.root"

    fout = ROOT.TFile.Open(str(path), "RECREATE")

    edges = np.asarray(eta_edges, dtype=np.float64)

    for sample in samples:
        safe = "".join(
            ch if ch.isalnum() or ch in "._-" else "_"
            for ch in sample["label"]
        )

        h_offset = ROOT.TH1D(
            f"offset_{safe}",
            "",
            len(edges) - 1,
            edges,
        )
        h_sigma = ROOT.TH1D(
            f"sigma_{safe}",
            "",
            len(edges) - 1,
            edges,
        )
        h_response = ROOT.TH1D(
            f"responseMedian_{safe}",
            "",
            len(edges) - 1,
            edges,
        )
        h_n = ROOT.TH1D(
            f"nProbes_{safe}",
            "",
            len(edges) - 1,
            edges,
        )

        for ibin, result in enumerate(
            all_results[sample["label"]],
            1,
        ):
            if not result.valid:
                continue

            h_offset.SetBinContent(ibin, result.offset)

            if np.isfinite(result.offset_error):
                h_offset.SetBinError(ibin, result.offset_error)

            h_sigma.SetBinContent(ibin, result.sigma)
            h_response.SetBinContent(ibin, result.response_median)
            h_n.SetBinContent(ibin, result.n_used)

        h_offset.Write()
        h_sigma.Write()
        h_response.Write()
        h_n.Write()

    fout.Close()

    return path


# =============================================================================
# Ensemble / all-events mode
# =============================================================================

def ensemble_pt_edges(args):
    if args.offset_pt_bins is not None:
        return np.asarray(args.offset_pt_bins, dtype=float)

    canonical = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0]
    edges = [float(args.probe_pt_min)]
    edges += [
        x for x in canonical
        if args.probe_pt_min < x < args.probe_pt_max
    ]
    edges.append(float(args.probe_pt_max))
    return np.asarray(sorted(set(edges)), dtype=float)


def cpp_edges(values):
    return "std::vector<double>{" + ",".join(
        f"{float(x):.17g}" for x in values
    ) + "}"


def declare_ensemble_cpp():
    ROOT.gInterpreter.Declare(r'''
#include <ROOT/RVec.hxx>
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace ChargedOffsetEnsemble {

inline double median(std::vector<double> v) {
  if (v.empty()) return std::numeric_limits<double>::quiet_NaN();
  const std::size_t n = v.size();
  const std::size_t m = n / 2;
  std::nth_element(v.begin(), v.begin() + m, v.end());
  double out = v[m];
  if ((n % 2) == 0) {
    const auto lo = std::max_element(v.begin(), v.begin() + m);
    out = 0.5 * (out + *lo);
  }
  return out;
}

inline double robustSigma(const std::vector<double>& v, double center) {
  std::vector<double> d;
  d.reserve(v.size());
  for (const double x : v) d.push_back(std::abs(x - center));
  return 1.4826 * median(std::move(d));
}

inline float robustOffset(std::vector<double> v,
                          int minProbes,
                          double nSigma,
                          int maxIterations) {
  if (static_cast<int>(v.size()) < minProbes)
    return std::numeric_limits<float>::quiet_NaN();

  for (int iteration = 0; iteration < maxIterations; ++iteration) {
    const double center = median(v);
    const double sigma = robustSigma(v, center);
    if (!std::isfinite(sigma) || sigma <= 0.) break;

    const double upper = center + nSigma * sigma;
    const std::size_t oldSize = v.size();
    v.erase(std::remove_if(v.begin(), v.end(),
                           [upper](double x) { return x > upper; }),
            v.end());

    if (static_cast<int>(v.size()) < minProbes)
      return std::numeric_limits<float>::quiet_NaN();
    if (v.size() == oldSize) break;
  }

  return static_cast<float>(median(std::move(v)));
}

template <typename VEta, typename VEnergy, typename VPdg,
          typename VCharge, typename VPt, typename VFrac, typename VIso>
ROOT::VecOps::RVec<float> offsets(const VEta& eta,
                                  const VEnergy& energy,
                                  const VPdg& pdgId,
                                  const VCharge& charge,
                                  const VPt& ptTrk,
                                  const VFrac& caloFraction,
                                  const VIso& isolated,
                                  const std::vector<double>& etaEdges,
                                  const std::vector<double>& ptEdges,
                                  bool useAbsEta,
                                  bool requireIsolated,
                                  double responseScale,
                                  int minProbes,
                                  double nSigma,
                                  int maxIterations) {
  const int nEta = static_cast<int>(etaEdges.size()) - 1;
  const int nPt = static_cast<int>(ptEdges.size()) - 1;
  ROOT::VecOps::RVec<float> out(
      std::max(0, nEta) * std::max(0, nPt),
      std::numeric_limits<float>::quiet_NaN());

  if (nEta <= 0 || nPt <= 0) return out;
  const std::size_t n = eta.size();
  if (energy.size() != n || pdgId.size() != n || charge.size() != n ||
      ptTrk.size() != n || caloFraction.size() != n || isolated.size() != n)
    return out;

  std::vector<std::vector<double>> cells(nEta * nPt);

  for (std::size_t i = 0; i < n; ++i) {
    const int apid = std::abs(static_cast<int>(pdgId[i]));
    if (charge[i] == 0 || apid == 11 || apid == 13) continue;
    if (requireIsolated && !static_cast<bool>(isolated[i])) continue;

    const double pt = static_cast<double>(ptTrk[i]);
    const double frac = static_cast<double>(caloFraction[i]);
    if (!std::isfinite(pt) || !std::isfinite(frac) || frac <= 0.) continue;

    const double etaRaw = static_cast<double>(eta[i]);
    const double etaBinValue = useAbsEta ? std::abs(etaRaw) : etaRaw;

    const auto eit = std::upper_bound(
        etaEdges.begin(), etaEdges.end(), etaBinValue);
    if (eit == etaEdges.begin() || eit == etaEdges.end()) continue;
    const int iEta =
        static_cast<int>(std::distance(etaEdges.begin(), eit)) - 1;

    const auto pit = std::upper_bound(ptEdges.begin(), ptEdges.end(), pt);
    if (pit == ptEdges.begin() || pit == ptEdges.end()) continue;
    const int iPt =
        static_cast<int>(std::distance(ptEdges.begin(), pit)) - 1;

    const double caloEt =
        static_cast<double>(energy[i]) * frac / std::cosh(etaRaw);
    const double deltaPt = caloEt - responseScale * pt;
    if (!std::isfinite(deltaPt)) continue;

    cells[iEta * nPt + iPt].push_back(deltaPt);
  }

  for (int iEta = 0; iEta < nEta; ++iEta) {
    for (int iPt = 0; iPt < nPt; ++iPt) {
      const int k = iEta * nPt + iPt;
      out[k] = robustOffset(
          std::move(cells[k]), minProbes, nSigma, maxIterations);
    }
  }
  return out;
}

}  // namespace ChargedOffsetEnsemble
''')


def safe_sample_label(label):
    return "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in label
    )


def ensemble_branch_info(filename, args):
    branches, entries = tree_info(filename, args.tree)
    nvtx = detect_nvtx_branch(branches, args.nvtx_branch)
    c = args.collection

    names = {
        "eta": f"{c}_eta",
        "energy": f"{c}_energy",
        "pdgId": f"{c}_pdgId",
        "charge": f"{c}_charge",
        "ptTrk": f"{c}_ptTrk",
        "caloFraction": (
            f"{c}_caloFraction"
            if args.energy_source == "corrected"
            else f"{c}_rawCaloFraction"
        ),
        "isolated": f"{c}_isIsolatedChargedHadron",
    }

    required = [
        names["eta"], names["energy"], names["pdgId"],
        names["charge"], names["ptTrk"], names["caloFraction"],
    ]
    if args.probe_mode == "isolated":
        required.append(names["isolated"])

    missing = [x for x in required if x not in branches]
    if missing:
        raise RuntimeError(
            f"{filename}: missing all-event branches:\\n  "
            + "\\n  ".join(missing)
        )

    if args.min_nvtx is not None and nvtx is None:
        raise RuntimeError(
            f"{filename}: --min-nvtx requested but no Nvtx branch was found"
        )

    return branches, entries, nvtx, names


def book_stat_actions(node, column, name, args, all_actions):
    hist = node.Histo1D(
        ROOT.RDF.TH1DModel(
            name, "", args.offset_hist_bins,
            -args.delta_pt_range, args.delta_pt_range
        ),
        column,
    )
    mean = node.Mean(column)
    stddev = node.StdDev(column)
    count = node.Count()
    all_actions.extend([hist, mean, stddev, count])
    return {"hist": hist, "mean": mean, "stddev": stddev, "count": count}


def build_ensemble_graph(filename, label, args, eta_edges, pt_edges, isample):
    branches, entries, nvtx, names = ensemble_branch_info(filename, args)

    start = args.event
    if start >= entries:
        raise RuntimeError(f"{filename}: --event {start} is outside the tree")

    stop = entries
    if args.max_events > 0:
        stop = min(stop, start + args.max_events)

    df = ROOT.RDataFrame(args.tree, filename)
    if start != 0 or stop != entries:
        df = df.Range(start, stop)

    if args.min_nvtx is not None:
        df = df.Filter(
            f"static_cast<double>({nvtx}) > {args.min_nvtx:.17g}",
            "Nvtx cut",
        )

    if names["isolated"] in branches:
        df = df.Define("OffsetStudy_iso", names["isolated"])
    else:
        df = df.Define(
            "OffsetStudy_iso",
            f"ROOT::VecOps::RVec<int>({names['charge']}.size(),1)",
        )

    if nvtx is not None:
        df = df.Define("OffsetStudy_nvtx", f"static_cast<double>({nvtx})")
    else:
        df = df.Define("OffsetStudy_nvtx", "0.0")

    use_abs = "true" if args.absolute_eta else "false"
    require_iso = "true" if args.probe_mode == "isolated" else "false"

    common = (
        f"{names['eta']}, {names['energy']}, {names['pdgId']}, "
        f"{names['charge']}, {names['ptTrk']}, {names['caloFraction']}, "
        "OffsetStudy_iso"
    )
    settings = (
        f"{use_abs}, {require_iso}, {args.response_scale:.17g}, "
        f"{args.min_probes}, {args.n_sigma:.17g}, {args.max_iterations}"
    )

    df = df.Define(
        "OffsetStudy_etaOffsets",
        "ChargedOffsetEnsemble::offsets("
        + common
        + f", {cpp_edges(eta_edges)}, "
        + f"{cpp_edges([args.probe_pt_min, args.probe_pt_max])}, "
        + settings + ")",
    )
    df = df.Define(
        "OffsetStudy_ptOffsets",
        "ChargedOffsetEnsemble::offsets("
        + common
        + f", {cpp_edges([eta_edges[0], eta_edges[-1]])}, "
        + f"{cpp_edges(pt_edges)}, "
        + settings + ")",
    )
    df = df.Define(
        "OffsetStudy_gridOffsets",
        "ChargedOffsetEnsemble::offsets("
        + common
        + f", {cpp_edges(eta_edges)}, {cpp_edges(pt_edges)}, "
        + settings + ")",
    )

    n_eta = len(eta_edges) - 1
    n_pt = len(pt_edges) - 1

    for ieta in range(n_eta):
        df = df.Define(
            f"OffsetStudy_eta_{ieta}",
            f"static_cast<double>(OffsetStudy_etaOffsets[{ieta}])",
        )
    for ipt in range(n_pt):
        df = df.Define(
            f"OffsetStudy_pt_{ipt}",
            f"static_cast<double>(OffsetStudy_ptOffsets[{ipt}])",
        )
    for ieta in range(n_eta):
        for ipt in range(n_pt):
            k = ieta * n_pt + ipt
            df = df.Define(
                f"OffsetStudy_grid_{ieta}_{ipt}",
                f"static_cast<double>(OffsetStudy_gridOffsets[{k}])",
            )

    all_actions = []
    selected_count = df.Count()
    all_actions.append(selected_count)

    eta_actions = []
    for ieta in range(n_eta):
        col = f"OffsetStudy_eta_{ieta}"
        node = df.Filter(f"std::isfinite({col})")
        eta_actions.append(
            book_stat_actions(
                node, col, f"h_off_{isample}_eta{ieta}", args, all_actions
            )
        )

    pt_actions = []
    for ipt in range(n_pt):
        col = f"OffsetStudy_pt_{ipt}"
        node = df.Filter(f"std::isfinite({col})")
        pt_actions.append(
            book_stat_actions(
                node, col, f"h_off_{isample}_pt{ipt}", args, all_actions
            )
        )

    grid_actions = [[None] * n_pt for _ in range(n_eta)]
    for ieta in range(n_eta):
        for ipt in range(n_pt):
            col = f"OffsetStudy_grid_{ieta}_{ipt}"
            node = df.Filter(f"std::isfinite({col})")
            actions = book_stat_actions(
                node, col, f"h_off_{isample}_e{ieta}_p{ipt}", args, all_actions
            )
            profile = node.Profile1D(
                ROOT.RDF.TProfile1DModel(
                    f"p_nvtx_{isample}_e{ieta}_p{ipt}", "",
                    args.nvtx_plot_bins,
                    args.nvtx_plot_min,
                    args.nvtx_plot_max,
                ),
                "OffsetStudy_nvtx",
                col,
            )
            all_actions.append(profile)
            actions["profile_nvtx"] = profile
            grid_actions[ieta][ipt] = actions

    return {
        "filename": filename,
        "label": label,
        "nvtx_branch": nvtx,
        "range_start": start,
        "range_stop": stop,
        "selected_count": selected_count,
        "all_actions": all_actions,
        "eta_actions": eta_actions,
        "pt_actions": pt_actions,
        "grid_actions": grid_actions,
    }


def materialize_actions(actions, suffix):
    hist_value = actions["hist"].GetValue()
    hist = hist_value.Clone(f"{hist_value.GetName()}_{suffix}")
    hist.SetDirectory(0)

    n = int(actions["count"].GetValue())
    mean = float(actions["mean"].GetValue()) if n else float("nan")
    stddev = (
        float(actions["stddev"].GetValue())
        if n > 1 else float("nan")
    )
    out = {"hist": hist, "count": n, "mean": mean, "stddev": stddev}

    if "profile_nvtx" in actions:
        value = actions["profile_nvtx"].GetValue()
        profile = value.Clone(f"{value.GetName()}_{suffix}")
        profile.SetDirectory(0)
        out["profile_nvtx"] = profile

    return out


def execute_ensemble_graph(graph):
    ROOT.RDF.RunGraphs(graph["all_actions"])
    safe = safe_sample_label(graph["label"])

    eta = [
        materialize_actions(x, f"{safe}_eta{i}")
        for i, x in enumerate(graph["eta_actions"])
    ]
    pt = [
        materialize_actions(x, f"{safe}_pt{i}")
        for i, x in enumerate(graph["pt_actions"])
    ]
    grid = []
    for ieta, row in enumerate(graph["grid_actions"]):
        grid.append([
            materialize_actions(x, f"{safe}_e{ieta}_p{ipt}")
            for ipt, x in enumerate(row)
        ])

    return {
        "filename": graph["filename"],
        "label": graph["label"],
        "nvtx_branch": graph["nvtx_branch"],
        "range_start": graph["range_start"],
        "range_stop": graph["range_stop"],
        "selected_events": int(graph["selected_count"].GetValue()),
        "eta": eta,
        "pt": pt,
        "grid": grid,
    }


def ensemble_sem(stat):
    if stat["count"] <= 1 or not np.isfinite(stat["stddev"]):
        return 0.0
    return stat["stddev"] / math.sqrt(stat["count"])


def clone_normalized(hist, name):
    h = hist.Clone(name)
    h.SetDirectory(0)
    integral = h.Integral(1, h.GetNbinsX())
    if integral > 0:
        h.Scale(1.0 / integral)
    return h


def draw_ensemble_distribution(samples, stat_getter, title, output):
    prepared = []
    colors = palette()

    for i, sample in enumerate(samples):
        stat = stat_getter(sample)
        if stat["count"] <= 0:
            continue
        h = clone_normalized(
            stat["hist"],
            f"h_draw_{i}_{abs(hash(str(output))) % 1000000}",
        )
        prepared.append((sample, stat, h))

    if not prepared:
        return False

    c = ROOT.TCanvas(
        f"c_dist_{abs(hash(str(output))) % 1000000}", "", 790, 610
    )
    c.SetTicks(1, 1)
    ymax = max(h.GetMaximum() for _, _, h in prepared)

    leg = ROOT.TLegend(0.54, 0.68, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    first = True
    for i, (sample, stat, h) in enumerate(prepared):
        h.SetStats(False)
        h.SetLineWidth(2)
        h.SetLineColor(colors[i % len(colors)])
        h.GetXaxis().SetTitle("Event-level robust offset O [GeV]")
        h.GetYaxis().SetTitle("Fraction of events / bin")
        h.SetMaximum(max(1e-4, ymax * 1.35))
        h.Draw("hist" if first else "hist same")
        first = False
        leg.AddEntry(
            h,
            f"{sample['label']}: N={stat['count']}, <O>={stat['mean']:+.3f}",
            "l",
        )

    leg.Draw()
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.DrawLatex(0.13, 0.93, title)

    output.parent.mkdir(parents=True, exist_ok=True)
    c.SaveAs(str(output))
    c.Close()
    return True


def draw_ensemble_curves(curves, xtitle, title, output):
    curves = [c for c in curves if len(c["x"]) > 0]
    if not curves:
        return False

    xs = [x for c in curves for x in c["x"] if np.isfinite(x)]
    ys = [y for c in curves for y in c["y"] if np.isfinite(y)]
    if not xs or not ys:
        return False

    xmin, xmax = min(xs), max(xs)
    if xmax <= xmin:
        xmin -= 0.5
        xmax += 0.5
    ymin, ymax = min(ys), max(ys)
    span = max(ymax - ymin, 0.05)

    c = ROOT.TCanvas(
        f"c_curve_{abs(hash(str(output))) % 1000000}", "", 800, 620
    )
    c.SetTicks(1, 1)

    frame = ROOT.TH1D(
        f"frame_curve_{abs(hash(str(output))) % 1000000}",
        "", 100, xmin, xmax
    )
    frame.SetDirectory(0)
    frame.SetStats(False)
    frame.GetXaxis().SetTitle(xtitle)
    frame.GetYaxis().SetTitle("Average event-level offset <O> [GeV]")
    frame.SetMinimum(ymin - 0.30 * span)
    frame.SetMaximum(ymax + 0.35 * span)
    frame.Draw()

    colors = palette()
    keep = [frame]
    leg = ROOT.TLegend(0.61, 0.68, 0.89, 0.89)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for i, curve in enumerate(curves):
        x = np.asarray(curve["x"], dtype=np.float64)
        y = np.asarray(curve["y"], dtype=np.float64)
        ex = np.zeros(len(x), dtype=np.float64)
        ey = np.asarray(curve["ey"], dtype=np.float64)
        g = ROOT.TGraphErrors(len(x), x, y, ex, ey)
        g.SetMarkerStyle(20 + (i % 5))
        g.SetMarkerSize(0.95)
        g.SetMarkerColor(colors[i % len(colors)])
        g.SetLineColor(colors[i % len(colors)])
        g.SetLineWidth(2)
        g.Draw("LP SAME")
        keep.append(g)
        leg.AddEntry(g, curve["label"], "lp")

    zero = ROOT.TLine(xmin, 0.0, xmax, 0.0)
    zero.SetLineStyle(2)
    zero.SetLineColor(ROOT.kGray + 2)
    zero.Draw()
    keep.append(zero)

    leg.Draw()
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.DrawLatex(0.13, 0.93, title)

    output.parent.mkdir(parents=True, exist_ok=True)
    c.SaveAs(str(output))
    c.Close()
    return True


def profile_points(profile, min_events):
    x, y, ey = [], [], []
    for ibin in range(1, profile.GetNbinsX() + 1):
        n = float(profile.GetBinEntries(ibin))
        if n < min_events:
            continue
        value = float(profile.GetBinContent(ibin))
        if not np.isfinite(value):
            continue
        x.append(float(profile.GetXaxis().GetBinCenter(ibin)))
        y.append(value)
        error = float(profile.GetBinError(ibin))
        ey.append(error if np.isfinite(error) else 0.0)
    return x, y, ey


def make_ensemble_plots(samples, eta_edges, pt_edges, args, outdir):
    base = outdir / "all_events"
    distdir = base / "offset_distributions"
    avgdir = base / "average_offsets"
    nvdir = base / "offset_vs_nvtx"

    eta_centers = 0.5 * (eta_edges[:-1] + eta_edges[1:])
    pt_centers = 0.5 * (pt_edges[:-1] + pt_edges[1:])
    eta_symbol = "|#eta|" if args.absolute_eta else "#eta"

    # Event-by-event offset distributions
    for ieta, (elo, ehi) in enumerate(zip(eta_edges[:-1], eta_edges[1:])):
        draw_ensemble_distribution(
            samples,
            lambda s, ieta=ieta: s["eta"][ieta],
            (
                f"Per-event offsets: {elo:g} < {eta_symbol} < {ehi:g}, "
                f"{args.probe_pt_min:g} < p_{{T}}^{{track}} "
                f"< {args.probe_pt_max:g} GeV"
            ),
            distdir / "by_eta" / f"{eta_tag(elo, ehi)}.png",
        )

    for ipt, (plo, phi) in enumerate(zip(pt_edges[:-1], pt_edges[1:])):
        draw_ensemble_distribution(
            samples,
            lambda s, ipt=ipt: s["pt"][ipt],
            f"Per-event offsets: {plo:g} < p_{{T}}^{{track}} < {phi:g} GeV",
            distdir / "by_pt" / f"pt_{plo:g}_{phi:g}.png",
        )

    for ieta, (elo, ehi) in enumerate(zip(eta_edges[:-1], eta_edges[1:])):
        for ipt, (plo, phi) in enumerate(zip(pt_edges[:-1], pt_edges[1:])):
            draw_ensemble_distribution(
                samples,
                lambda s, ieta=ieta, ipt=ipt: s["grid"][ieta][ipt],
                (
                    f"Per-event offsets: {elo:g} < {eta_symbol} < {ehi:g}, "
                    f"{plo:g} < p_{{T}}^{{track}} < {phi:g} GeV"
                ),
                distdir / "by_eta_pt" / eta_tag(elo, ehi)
                / f"pt_{plo:g}_{phi:g}.png",
            )

    # Average offset vs eta, inclusive pT
    curves = []
    for sample in samples:
        x, y, ey = [], [], []
        for center, stat in zip(eta_centers, sample["eta"]):
            if stat["count"] < args.min_events_per_average:
                continue
            x.append(float(center))
            y.append(stat["mean"])
            ey.append(ensemble_sem(stat))
        curves.append({"label": sample["label"], "x": x, "y": y, "ey": ey})

    draw_ensemble_curves(
        curves,
        eta_symbol,
        "Average event-level offset vs #eta",
        avgdir / "average_offset_vs_eta.png",
    )

    # Average offset vs pT, inclusive eta
    curves = []
    for sample in samples:
        x, y, ey = [], [], []
        for center, stat in zip(pt_centers, sample["pt"]):
            if stat["count"] < args.min_events_per_average:
                continue
            x.append(float(center))
            y.append(stat["mean"])
            ey.append(ensemble_sem(stat))
        curves.append({"label": sample["label"], "x": x, "y": y, "ey": ey})

    draw_ensemble_curves(
        curves,
        "p_{T}^{track} [GeV]",
        "Average event-level offset vs probe p_{T}",
        avgdir / "average_offset_vs_pt.png",
    )

    # Split pT dependence by eta and eta dependence by pT, one file at a time.
    for sample in samples:
        safe = safe_sample_label(sample["label"])

        curves = []
        for ieta, (elo, ehi) in enumerate(zip(eta_edges[:-1], eta_edges[1:])):
            x, y, ey = [], [], []
            for center, stat in zip(pt_centers, sample["grid"][ieta]):
                if stat["count"] < args.min_events_per_average:
                    continue
                x.append(float(center))
                y.append(stat["mean"])
                ey.append(ensemble_sem(stat))
            curves.append({
                "label": f"{elo:g} < eta < {ehi:g}",
                "x": x, "y": y, "ey": ey,
            })

        draw_ensemble_curves(
            curves,
            "p_{T}^{track} [GeV]",
            f"{sample['label']}: average offset vs p_{{T}} in #eta regions",
            avgdir / f"average_offset_vs_pt_by_eta_{safe}.png",
        )

        curves = []
        for ipt, (plo, phi) in enumerate(zip(pt_edges[:-1], pt_edges[1:])):
            x, y, ey = [], [], []
            for center, row in zip(eta_centers, sample["grid"]):
                stat = row[ipt]
                if stat["count"] < args.min_events_per_average:
                    continue
                x.append(float(center))
                y.append(stat["mean"])
                ey.append(ensemble_sem(stat))
            curves.append({
                "label": f"{plo:g} < pT < {phi:g}",
                "x": x, "y": y, "ey": ey,
            })

        draw_ensemble_curves(
            curves,
            eta_symbol,
            f"{sample['label']}: average offset vs #eta in p_{{T}} regions",
            avgdir / f"average_offset_vs_eta_by_pt_{safe}.png",
        )

        if sample["nvtx_branch"] is None:
            continue

        # Nvtx: one plot per eta ring with pT-region curves.
        for ieta, (elo, ehi) in enumerate(zip(eta_edges[:-1], eta_edges[1:])):
            curves = []
            for ipt, (plo, phi) in enumerate(zip(pt_edges[:-1], pt_edges[1:])):
                x, y, ey = profile_points(
                    sample["grid"][ieta][ipt]["profile_nvtx"],
                    args.min_events_per_average,
                )
                curves.append({
                    "label": f"{plo:g} < pT < {phi:g}",
                    "x": x, "y": y, "ey": ey,
                })

            draw_ensemble_curves(
                curves,
                sample["nvtx_branch"],
                (
                    f"{sample['label']}: average offset vs N_{{vtx}}, "
                    f"{elo:g} < {eta_symbol} < {ehi:g}"
                ),
                nvdir / safe / "by_eta" / f"{eta_tag(elo, ehi)}.png",
            )

        # Nvtx: one plot per pT region with eta-region curves.
        for ipt, (plo, phi) in enumerate(zip(pt_edges[:-1], pt_edges[1:])):
            curves = []
            for ieta, (elo, ehi) in enumerate(zip(eta_edges[:-1], eta_edges[1:])):
                x, y, ey = profile_points(
                    sample["grid"][ieta][ipt]["profile_nvtx"],
                    args.min_events_per_average,
                )
                curves.append({
                    "label": f"{elo:g} < eta < {ehi:g}",
                    "x": x, "y": y, "ey": ey,
                })

            draw_ensemble_curves(
                curves,
                sample["nvtx_branch"],
                (
                    f"{sample['label']}: average offset vs N_{{vtx}}, "
                    f"{plo:g} < p_{{T}}^{{track}} < {phi:g} GeV"
                ),
                nvdir / safe / "by_pt" / f"pt_{plo:g}_{phi:g}.png",
            )


def write_ensemble_csv(samples, eta_edges, pt_edges, args, outdir):
    base = outdir / "all_events"
    base.mkdir(parents=True, exist_ok=True)

    summary = base / "offset_ensemble_summary.csv"
    fields = [
        "file", "label", "scope",
        "eta_min", "eta_max", "pt_min", "pt_max",
        "n_events", "mean_offset_GeV", "std_offset_GeV", "sem_offset_GeV",
    ]
    rows = []

    for sample in samples:
        for ieta, stat in enumerate(sample["eta"]):
            rows.append({
                "file": sample["filename"], "label": sample["label"],
                "scope": "eta",
                "eta_min": eta_edges[ieta], "eta_max": eta_edges[ieta + 1],
                "pt_min": args.probe_pt_min, "pt_max": args.probe_pt_max,
                "n_events": stat["count"], "mean_offset_GeV": stat["mean"],
                "std_offset_GeV": stat["stddev"], "sem_offset_GeV": ensemble_sem(stat),
            })
        for ipt, stat in enumerate(sample["pt"]):
            rows.append({
                "file": sample["filename"], "label": sample["label"],
                "scope": "pt",
                "eta_min": eta_edges[0], "eta_max": eta_edges[-1],
                "pt_min": pt_edges[ipt], "pt_max": pt_edges[ipt + 1],
                "n_events": stat["count"], "mean_offset_GeV": stat["mean"],
                "std_offset_GeV": stat["stddev"], "sem_offset_GeV": ensemble_sem(stat),
            })
        for ieta, row in enumerate(sample["grid"]):
            for ipt, stat in enumerate(row):
                rows.append({
                    "file": sample["filename"], "label": sample["label"],
                    "scope": "eta_pt",
                    "eta_min": eta_edges[ieta], "eta_max": eta_edges[ieta + 1],
                    "pt_min": pt_edges[ipt], "pt_max": pt_edges[ipt + 1],
                    "n_events": stat["count"], "mean_offset_GeV": stat["mean"],
                    "std_offset_GeV": stat["stddev"], "sem_offset_GeV": ensemble_sem(stat),
                })

    with summary.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    nvtx_csv = base / "offset_vs_nvtx.csv"
    nv_fields = [
        "file", "label", "eta_min", "eta_max", "pt_min", "pt_max",
        "nvtx_center", "n_events", "mean_offset_GeV", "mean_offset_error_GeV",
    ]
    nv_rows = []

    for sample in samples:
        if sample["nvtx_branch"] is None:
            continue
        for ieta, row in enumerate(sample["grid"]):
            for ipt, stat in enumerate(row):
                p = stat["profile_nvtx"]
                for ibin in range(1, p.GetNbinsX() + 1):
                    n = float(p.GetBinEntries(ibin))
                    if n <= 0:
                        continue
                    nv_rows.append({
                        "file": sample["filename"], "label": sample["label"],
                        "eta_min": eta_edges[ieta], "eta_max": eta_edges[ieta + 1],
                        "pt_min": pt_edges[ipt], "pt_max": pt_edges[ipt + 1],
                        "nvtx_center": p.GetXaxis().GetBinCenter(ibin),
                        "n_events": n,
                        "mean_offset_GeV": p.GetBinContent(ibin),
                        "mean_offset_error_GeV": p.GetBinError(ibin),
                    })

    with nvtx_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=nv_fields)
        w.writeheader()
        w.writerows(nv_rows)

    return summary, nvtx_csv


def save_ensemble_root(samples, outdir):
    path = outdir / "all_events" / "offsetEnsemble.root"
    path.parent.mkdir(parents=True, exist_ok=True)
    fout = ROOT.TFile.Open(str(path), "RECREATE")

    for sample in samples:
        d = fout.mkdir(safe_sample_label(sample["label"]))
        d.cd()
        for ieta, stat in enumerate(sample["eta"]):
            stat["hist"].Write(f"offset_eta_{ieta}")
        for ipt, stat in enumerate(sample["pt"]):
            stat["hist"].Write(f"offset_pt_{ipt}")
        gd = d.mkdir("eta_pt")
        gd.cd()
        for ieta, row in enumerate(sample["grid"]):
            for ipt, stat in enumerate(row):
                stat["hist"].Write(f"offset_eta{ieta}_pt{ipt}")
                stat["profile_nvtx"].Write(f"offsetVsNvtx_eta{ieta}_pt{ipt}")
        fout.cd()

    fout.Close()
    return path


def run_all_events_mode(args, eta_edges, labels):
    declare_ensemble_cpp()
    pt_edges = ensemble_pt_edges(args)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("All-event mode")
    print(f"  start entry       : {args.event}")
    print(f"  max raw entries   : {args.max_events}")
    print(
        f"  Nvtx filter       : "
        + (
            f"Nvtx > {args.min_nvtx:g}"
            if args.min_nvtx is not None else "none"
        )
    )
    print(
        "  pT study edges    : "
        + ", ".join(f"{x:g}" for x in pt_edges)
        + " GeV"
    )
    print(
        "  event estimator   : robust median(E_T^calo - "
        f"{args.response_scale:g}*pT_track)"
    )

    if args.energy_source == "raw" and args.probe_mode == "charged":
        print(
            "  NOTE: raw + charged can still have low effective statistics; "
            "for all charged PackedCandidates, compare with "
            "--energy-source corrected."
        )

    graphs = [
        build_ensemble_graph(
            filename, label, args, eta_edges, pt_edges, i
        )
        for i, (filename, label) in enumerate(zip(args.inputs, labels))
    ]

    samples = []
    for graph in tqdm(graphs, desc="Running RDataFrame", unit="file"):
        sample = execute_ensemble_graph(graph)
        samples.append(sample)
        print(
            f"\\n{sample['label']}: {sample['selected_events']} selected events "
            f"from entries {sample['range_start']}:{sample['range_stop']}"
        )

    print("\\nMaking ensemble distributions and averages...")
    make_ensemble_plots(samples, eta_edges, pt_edges, args, outdir)
    summary, nvtx_csv = write_ensemble_csv(
        samples, eta_edges, pt_edges, args, outdir
    )

    root_path = None
    if args.save_root:
        root_path = save_ensemble_root(samples, outdir)

    print(f"\\nOutput:            {outdir / 'all_events'}")
    print(f"Ensemble summary:  {summary}")
    print(f"Nvtx table:        {nvtx_csv}")
    if root_path is not None:
        print(f"ROOT output:       {root_path}")
    print(
        "Each valid event-level offset contributes once to the averages; "
        "events with more charged probes do not receive a larger weight."
    )


def main():
    args = parse_args()
    eta_edges = validate_args(args)
    labels = labels_for(args)

    ROOT.gROOT.SetBatch(True)
    ROOT.TH1.AddDirectory(False)

    if args.all_events:
        run_all_events_mode(args, eta_edges, labels)
        return

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    rings_dir = outdir / "rings"
    rings_dir.mkdir(exist_ok=True)

    print("Estimator:")
    print(
        "  deltaPt = E_T^calo - "
        f"{args.response_scale:g} * pT_track"
    )
    print(
        "  offset = median(deltaPt) after one-sided positive-tail "
        f"clipping at {args.n_sigma:g} robust sigma"
    )
    print()

    samples = []

    for filename, label in tqdm(
        list(zip(args.inputs, labels)),
        desc="Reading selected events",
        unit="file",
    ):
        sample = read_event(filename, label, args)
        samples.append(sample)

        nvtx_text = ""

        if (
            sample["nvtx_branch"] is not None
            and np.isfinite(sample["nvtx"])
        ):
            nvtx_text = (
                f", {sample['nvtx_branch']}={sample['nvtx']:g}"
            )

        print(
            f"{label}: entry {sample['entry']}{nvtx_text}; "
            f"PFCands={len(sample['pt'])}; "
            f"selected probes={np.count_nonzero(sample['probe_mask'])}"
        )

    all_results = {
        sample["label"]: []
        for sample in samples
    }

    ring_jobs = list(zip(eta_edges[:-1], eta_edges[1:]))

    print()
    print("Estimating ring offsets...")

    for ieta, (eta_lo, eta_hi) in enumerate(
        tqdm(
            ring_jobs,
            desc="Eta rings",
            unit="ring",
        )
    ):
        ring_dir = rings_dir / eta_tag(eta_lo, eta_hi)
        ring_dir.mkdir(exist_ok=True)

        items = []

        for sample in samples:
            ring = ring_payload(sample, eta_lo, eta_hi)

            result = estimate_offset(
                ring["deltaPt"],
                ring["response"],
                ring["trackPt"],
                ring["caloEt"],
                ring["ecalEt"],
                ring["hcalEt"],
                args.min_probes,
                args.n_sigma,
                args.max_iterations,
            )

            all_results[sample["label"]].append(result)
            items.append((sample, ring, result))

            if result.valid:
                print(
                    f"{sample['label']:18s} "
                    f"eta [{eta_lo:5.2f},{eta_hi:5.2f}): "
                    f"N={result.n_used:3d}/{result.n_total:3d}, "
                    f"rej={result.n_rejected:2d}, "
                    f"O={result.offset:+.4f} GeV, "
                    f"sigma={result.sigma:.4f}, "
                    f"median(Ecalo/p)={result.response_median:.4f}"
                )
            else:
                print(
                    f"{sample['label']:18s} "
                    f"eta [{eta_lo:5.2f},{eta_hi:5.2f}): "
                    f"INVALID (N={result.n_total})"
                )

        draw_delta_hist(
            items,
            eta_lo,
            eta_hi,
            args,
            ring_dir,
            logy=False,
        )

        if not args.linear_only:
            draw_delta_hist(
                items,
                eta_lo,
                eta_hi,
                args,
                ring_dir,
                logy=True,
            )

        draw_delta_vs_phi(
            items,
            eta_lo,
            eta_hi,
            args,
            ring_dir,
        )

        draw_response_hist(
            items,
            eta_lo,
            eta_hi,
            args,
            ring_dir,
        )

        draw_calo_vs_track(
            items,
            eta_lo,
            eta_hi,
            args,
            ring_dir,
        )

        draw_calo_components(
            items,
            eta_lo,
            eta_hi,
            args,
            ring_dir,
        )

    print()
    print("Drawing eta summaries...")

    summary_graph(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
        "offset",
        "Robust offset O [GeV]",
        "offset_vs_eta.png",
        with_errors=True,
    )

    summary_graph(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
        "sigma",
        "Robust width of #Delta p_{T} [GeV]",
        "sigma_vs_eta.png",
    )

    summary_graph(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
        "response_median",
        "Median E_{T}^{calo} / p_{T}^{track}",
        "response_median_vs_eta.png",
    )

    summary_graph(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
        "n_used",
        "Accepted charged-hadron probes",
        "n_used_vs_eta.png",
    )

    summary_graph(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
        "n_rejected",
        "Rejected positive-tail probes",
        "n_rejected_vs_eta.png",
    )

    csv_path = write_csv(
        samples,
        all_results,
        eta_edges,
        args,
        outdir,
    )

    root_path = None

    if args.save_root:
        root_path = save_root(
            samples,
            all_results,
            eta_edges,
            args,
            outdir,
        )

    print()
    print(f"Output directory: {outdir}")
    print(f"Summary CSV:      {csv_path}")

    if root_path is not None:
        print(f"ROOT output:      {root_path}")

    print()
    print("Main quantity:")
    print(
        "  O(eta) = robust median[ "
        "E_T^calo,corr - R*pT_track ]"
    )
    print(
        f"  with R={args.response_scale:g} unless changed with "
        "--response-scale."
    )
    print()
    print(
        "Use response_median_vs_eta.png and each ring's "
        "caloEt_over_trackPt.png / caloEt_vs_trackPt.png to validate "
        "whether R=1 is a good approximation before interpreting O as a "
        "physical pileup offset."
    )


if __name__ == "__main__":
    main()
