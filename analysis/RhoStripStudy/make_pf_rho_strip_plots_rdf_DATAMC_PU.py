#!/usr/bin/env python3
# PROGRESS_VERIFIED: contains --progress argparse option and ROOT.RDF.Experimental.AddProgressBar hook.
"""
make_pf_rho_strip_plots_rdf.py

RDataFrame version of make_pf_rho_strip_plots.py.

This version can also book an optional MC input, draw Data/MC comparison
plots, and derive event-by-event MC pileup weights from the nPV distribution.

The heavy event processing is expressed as ROOT.RDataFrame transformations and
lazy actions.  There is no Python `for event in tree` / `tree.GetEntry(event)`
loop for the physics aggregation; per-event vector reductions are compiled C++
helpers called by RDataFrame and can run with ROOT implicit multi-threading.

Example:
  python3 make_pf_rho_strip_plots_rdf.py pico.root \
    -o pf_rho_strip_plots_rdf \
    --root-output pf_rho_strip_plots_rdf.root \
    --prefix PFRhoStrp \
    --nvtx-branch PV_npvsGood \
    --threads 0

Notes:
  * Python loops remain only for setup/bookkeeping/plot drawing: looping over
    flavors, vertex categories, eta bins, and output formats.
  * A small setup scan is used only to discover static eta/phi geometry and
    construct variable-bin axes. The number of scanned events is configurable
    with --geometry-scan-events and defaults to 25.
  * RDataFrame booked actions are triggered together after booking, so ROOT can
    evaluate them in shared event loops.
"""

import argparse
import math
import os
from array import array
from dataclasses import dataclass
from typing import Optional

import ROOT


FLAVORS = [
    ("All", ""),
    ("ChargedHadron", "ChargedHadron"),
    ("NeutralHadron", "NeutralHadron"),
    ("Photon", "Photon"),
    ("Electron", "Electron"),
    ("Muon", "Muon"),
    # ("Other", "Other"),
]

STACK_FLAVORS = [
    ("ChargedHadron", "ChargedHadron"),
    ("NeutralHadron", "NeutralHadron"),
    ("Photon", "Photon"),
    ("Electron", "Electron"),
    ("Muon", "Muon"),
    # ("Other", "Other"),
]

COLORS = {
    "All": ROOT.kBlack,
    "ChargedHadron": ROOT.kRed + 1,
    "NeutralHadron": ROOT.kBlue + 1,
    "Photon": ROOT.kOrange + 1,
    "Electron": ROOT.kGreen + 2,
    "Muon": ROOT.kMagenta + 1,
    # "Other": ROOT.kGray + 2,
}

RESOLVED_BRANCHES = {}


@dataclass
class VertexBin:
    name: str
    low: Optional[int]
    high: Optional[int]
    inclusive: bool = False

    def filter_expression(self, npv_col="rdf_npv"):
        if self.inclusive:
            return "true"
        if self.low is None or self.high is None:
            return "false"
        if self.high == 100:
            return f"({npv_col} >= {self.low} && {npv_col} <= {self.high})"
        return f"({npv_col} >= {self.low} && {npv_col} < {self.high})"


def _script_dir():
    try:
        return os.path.abspath(os.path.dirname(__file__))
    except NameError:
        return os.getcwd()


def _abs_user_path(path):
    return os.path.abspath(os.path.expanduser(path))


def _cpp_include_path(path):
    # ROOT/Cling accepts POSIX-style paths in #include even on most platforms.
    return path.replace('\\', '/').replace('"', '\\"')


def load_cpp_helpers(args):
    """Load the external C++ helper header/library used by RDataFrame.

    The helper functions are mostly templated, so Cling must see the header even
    when a precompiled shared library is also loaded.  The library option is
    useful for packaging and for forcing the helper translation unit to be built
    with normal compiler diagnostics/optimization.
    """
    script_dir = _script_dir()
    header = args.cpp_helpers_header or os.path.join(script_dir, "PFRhoStripRDFHelpers.h")
    source = args.cpp_helpers_source or os.path.join(script_dir, "PFRhoStripRDFHelpers.cc")
    library = args.cpp_helpers_library or ""

    header = _abs_user_path(header)
    source = _abs_user_path(source)
    if library:
        library = _abs_user_path(library)

    if not os.path.exists(header):
        raise RuntimeError(
            "Could not find C++ helper header: {}\n"
            "Place PFRhoStripRDFHelpers.h next to this script, or pass --cpp-helpers-header.".format(header)
        )

    include_dir = os.path.dirname(header)
    ROOT.gInterpreter.AddIncludePath(include_dir)

    if args.compile_cpp_helpers:
        if not os.path.exists(source):
            raise RuntimeError(
                "Could not find C++ helper source: {}\n"
                "Place PFRhoStripRDFHelpers.cc next to this script, or pass --cpp-helpers-source.".format(source)
            )
        print("[info] compiling C++ helpers with ROOT ACLiC: {}".format(source))
        rc = ROOT.gSystem.CompileMacro(source, "kO")
        if not rc:
            raise RuntimeError("ROOT ACLiC failed to compile C++ helpers: {}".format(source))

    if library:
        print("[info] loading C++ helper library: {}".format(library))
        status = ROOT.gSystem.Load(library)
        if status < 0:
            raise RuntimeError("ROOT failed to load C++ helper library: {}".format(library))

    # Keep the template definitions visible to Cling for RDF expressions.
    ROOT.gInterpreter.Declare('#include "{}"'.format(_cpp_include_path(header)))
    print("[info] included C++ helper header: {}".format(header))


# Backward-compatible name used by earlier revisions of this script.
def declare_cpp_helpers():
    class _Args:
        cpp_helpers_header = ""
        cpp_helpers_source = ""
        cpp_helpers_library = ""
        compile_cpp_helpers = False
    load_cpp_helpers(_Args())


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def safe_name(x):
    return str(x).replace("-", "m").replace("+", "p").replace(".", "p")


def safe_col(x):
    return safe_name(x).replace("/", "_").replace(" ", "_")


def all_branch_names(tree):
    return [br.GetName() for br in tree.GetListOfBranches()]


def resolve_branch_name(tree, name, required=False):
    if name in RESOLVED_BRANCHES:
        return RESOLVED_BRANCHES[name]
    if tree.GetBranch(name) or tree.GetLeaf(name):
        RESOLVED_BRANCHES[name] = name
        return name
    lname = name.lower()
    matches = [b for b in all_branch_names(tree) if b.lower() == lname]
    if matches:
        RESOLVED_BRANCHES[name] = matches[0]
        if matches[0] != name:
            print("[info] resolved branch '{}' -> '{}'".format(name, matches[0]))
        return matches[0]
    if required:
        nearby = [b for b in all_branch_names(tree) if "rho" in b.lower() or "pfrho" in b.lower()]
        raise RuntimeError("Missing branch: {}\nNearby rho branches:\n  {}".format(name, "\n  ".join(nearby[:100])))
    return None


def branch_exists(tree, name):
    return resolve_branch_name(tree, name, required=False) is not None


def find_first_branch(tree, candidates):
    for name in candidates:
        if branch_exists(tree, name):
            return name
    return None


def rho_branch(prefix, suffix):
    return "{}_rho{}".format(prefix, suffix) if suffix else "{}_rho".format(prefix)


def n_branch(prefix, suffix):
    return "{}_n{}".format(prefix, suffix) if suffix else "{}_n".format(prefix)


def sumpt_branch(prefix, suffix):
    return "{}_sumPt{}".format(prefix, suffix) if suffix else "{}_sumPt".format(prefix)


def get_vector(tree, branch_name):
    actual = RESOLVED_BRANCHES.get(branch_name, branch_name)
    return getattr(tree, actual)


def save_canvas(canvas, out_dir, name, formats):
    mkdir(out_dir)
    for fmt in formats:
        canvas.SaveAs(os.path.join(out_dir, "{}.{}".format(name, fmt)))


def style_hist(hist, flavor, marker=True, fill=False):
    color = COLORS.get(flavor, ROOT.kBlack)
    hist.SetLineColor(color)
    hist.SetMarkerColor(color)
    hist.SetLineWidth(2)
    if marker:
        hist.SetMarkerStyle(20)
        hist.SetMarkerSize(2.0)
    if fill:
        hist.SetFillColor(color)
        hist.SetFillStyle(1001)


def make_eta_display_edges(eta_info):
    """Build non-overlapping display edges for eta plots."""
    ordered = sorted(eta_info, key=lambda x: x[1])

    if len(ordered) == 1:
        _, eta_min, eta_max, eta = ordered[0]
        if eta_max > eta_min:
            return [float(eta_min), float(eta_max)], ordered
        return [float(eta) - 0.5, float(eta) + 0.5], ordered

    edges = [float(ordered[0][1])]
    for i in range(1, len(ordered)):
        prev_eta = float(ordered[i - 1][3])
        this_eta = float(ordered[i][3])
        this_eta_min = float(ordered[i][1])
        boundary = this_eta_min
        if boundary <= edges[-1]:
            boundary = 0.5 * (prev_eta + this_eta)
        if boundary <= edges[-1]:
            boundary = edges[-1] + 1e-5
        edges.append(boundary)

    last_eta_max = float(ordered[-1][2])
    if last_eta_max <= edges[-1]:
        last_eta = float(ordered[-1][3])
        prev_eta = float(ordered[-2][3])
        last_eta_max = last_eta + 0.5 * abs(last_eta - prev_eta)
    if last_eta_max <= edges[-1]:
        last_eta_max = edges[-1] + 1e-5
    edges.append(last_eta_max)
    return edges, ordered


def make_phi_edges(phi_info):
    if not phi_info:
        return [-math.pi, math.pi], []
    use_edges = all((pmax > pmin) for _, pmin, pmax, _, _ in phi_info)
    if use_edges:
        ordered = sorted(phi_info, key=lambda x: x[1])
        edges = []
        for i, (_, pmin, pmax, _, _) in enumerate(ordered):
            if i == 0:
                edges.append(float(pmin))
            edges.append(float(pmax))
        clean_edges = [edges[0]]
        for e in edges[1:]:
            if e <= clean_edges[-1]:
                e = clean_edges[-1] + 1e-5
            clean_edges.append(e)
        return clean_edges, ordered
    ordered = sorted(phi_info, key=lambda x: x[3])
    # Fixed bins over [-pi, pi] if detailed phi edges are unavailable.
    nb = max(len(ordered), 1)
    step = (2.0 * math.pi) / nb
    edges = [-math.pi + i * step for i in range(nb + 1)]
    return edges, ordered


def profile_model_variable(name, title, edges):
    return (name, title, len(edges) - 1, array("d", [float(e) for e in edges]))


def profile_to_hist(profile, name, title=None):
    """Convert a TProfile/TProfile-derived result to a TH1D for THStack/writing."""
    nb = profile.GetNbinsX()
    edges = [profile.GetXaxis().GetBinLowEdge(1)]
    for ibin in range(1, nb + 1):
        edges.append(profile.GetXaxis().GetBinUpEdge(ibin))
    hist = ROOT.TH1D(name, title if title is not None else profile.GetTitle(), nb, array("d", [float(e) for e in edges]))
    hist.Sumw2()
    hist.SetStats(False)
    hist.GetXaxis().SetTitle(profile.GetXaxis().GetTitle())
    hist.GetYaxis().SetTitle(profile.GetYaxis().GetTitle())
    for ibin in range(1, nb + 1):
        hist.SetBinContent(ibin, profile.GetBinContent(ibin))
        hist.SetBinError(ibin, profile.GetBinError(ibin))
    return hist


def draw_individual(hist, out_dir, name, formats, logy=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    if logy:
        c.SetLogy()
    hist.Draw("E1")
    save_canvas(c, out_dir, name, formats)
    return c


def draw_overlay(hists, out_dir, name, title, ytitle, formats, logy=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    if logy:
        c.SetLogy()
    legend = ROOT.TLegend(0.58, 0.60, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    max_val = 0.0
    for _, hist in hists:
        max_val = max(max_val, hist.GetMaximum())
    first = True
    keep = []
    for flavor, hist in hists:
        h = hist.Clone("{}_overlay".format(hist.GetName()))
        keep.append(h)
        style_hist(h, flavor)
        h.SetTitle(title)
        h.GetYaxis().SetTitle(ytitle)
        if first:
            h.SetMaximum(max_val * 1.35 if max_val > 0 else 1.0)
            h.Draw("E1")
            first = False
        else:
            h.Draw("E1 SAME")
        legend.AddEntry(h, flavor, "lep")
    legend.Draw()
    c._keep = keep + [legend]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_stack(hists_by_flavor, all_hist, out_dir, name, title, ytitle, formats, logy=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    if logy:
        c.SetLogy()
    stack = ROOT.THStack("stack_{}".format(name), title)
    legend = ROOT.TLegend(0.60, 0.56, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    keep = []
    for flavor, hist in hists_by_flavor:
        h = hist.Clone("{}_stack".format(hist.GetName()))
        keep.append(h)
        style_hist(h, flavor, marker=False, fill=True)
        stack.Add(h, "HIST")
        legend.AddEntry(h, flavor, "f")
    stack.Draw("HIST")
    if hists_by_flavor:
        stack.GetXaxis().SetTitle(hists_by_flavor[0][1].GetXaxis().GetTitle())
    stack.GetYaxis().SetTitle(ytitle)
    if all_hist is not None:
        h_all = all_hist.Clone("{}_all_overlay".format(all_hist.GetName()))
        keep.append(h_all)
        style_hist(h_all, "All", marker=True, fill=False)
        h_all.SetFillStyle(0)
        h_all.Draw("E1 SAME")
        legend.AddEntry(h_all, "All", "lep")
    legend.Draw()
    c._keep = keep + [stack, legend]
    save_canvas(c, out_dir, name, formats)
    return c



DATA_MARKER_BY_FLAVOR = {
    "All": 21,              # square
    "ChargedHadron": 22,   # triangle up
    "NeutralHadron": 23,   # triangle down / diamond depending on ROOT font set
    "Photon": 33,
    "Electron": 34,
    "Muon": 29,
}


def _hist_maximum_for_drawing(hist):
    if hist is None:
        return 0.0
    try:
        return max(hist.GetMaximum(), 0.0)
    except Exception:
        return 0.0


def style_data_points(obj, flavor="All", marker=None):
    color = COLORS.get(flavor, ROOT.kBlack)
    obj.SetLineColor(color)
    obj.SetMarkerColor(color)
    obj.SetMarkerStyle(marker if marker is not None else DATA_MARKER_BY_FLAVOR.get(flavor, 21))
    obj.SetMarkerSize(1.25 if flavor == "All" else 1.10)
    obj.SetLineWidth(2)
    if hasattr(obj, "SetFillStyle"):
        obj.SetFillStyle(0)


def style_mc_line(obj, flavor="All", fill=False):
    color = COLORS.get(flavor, ROOT.kBlack)
    obj.SetLineColor(color)
    obj.SetMarkerColor(color)
    obj.SetLineWidth(2)
    if fill and hasattr(obj, "SetFillColor"):
        obj.SetFillColor(color)
        obj.SetFillStyle(1001)
    elif hasattr(obj, "SetFillStyle"):
        obj.SetFillStyle(0)


def draw_data_mc_hist(data_hist, mc_hist, out_dir, name, title, ytitle, formats,
                      data_label="Data", mc_label="MC", flavor="All", logy=False):
    """Draw one Data/MC comparison: data as markers, MC as line."""
    if data_hist is None or mc_hist is None:
        return None
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    if logy:
        c.SetLogy()

    d = data_hist.Clone("{}_data_cmp".format(data_hist.GetName()))
    m = mc_hist.Clone("{}_mc_cmp".format(mc_hist.GetName()))
    d.SetDirectory(0)
    m.SetDirectory(0)
    style_mc_line(m, flavor, fill=False)
    style_data_points(d, flavor)
    m.SetTitle(title)
    m.GetYaxis().SetTitle(ytitle)
    d.SetTitle(title)
    d.GetYaxis().SetTitle(ytitle)

    max_val = max(_hist_maximum_for_drawing(d), _hist_maximum_for_drawing(m))
    first = m
    first.SetMaximum(max_val * 1.35 if max_val > 0 else 1.0)
    if not logy:
        first.SetMinimum(0.0)
    first.Draw("HIST")
    d.Draw("E1 SAME")

    legend = ROOT.TLegend(0.58, 0.72, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.AddEntry(d, data_label, "lep")
    legend.AddEntry(m, mc_label, "l")
    legend.Draw()

    c._keep = [d, m, legend]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_data_mc_flavor_overlay(data_hists, mc_hists, flavors, out_dir, name, title, ytitle, formats,
                                data_label="Data", mc_label="MC", logy=False):
    """Draw all flavors, with MC as lines and data as markers."""
    c = ROOT.TCanvas("c_{}".format(name), "", 1100, 800)
    c.SetGrid()
    if logy:
        c.SetLogy()

    legend = ROOT.TLegend(0.54, 0.48, 0.90, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    keep = []
    max_val = 0.0
    for flavor in flavors:
        max_val = max(max_val,
                      _hist_maximum_for_drawing(data_hists.get(flavor)),
                      _hist_maximum_for_drawing(mc_hists.get(flavor)))

    first_drawn = False
    for flavor in flavors:
        mh = mc_hists.get(flavor)
        dh = data_hists.get(flavor)
        if mh is not None:
            m = mh.Clone("{}_{}_mc_flavor_cmp".format(mh.GetName(), safe_col(flavor)))
            m.SetDirectory(0)
            style_mc_line(m, flavor, fill=False)
            m.SetTitle(title)
            m.GetYaxis().SetTitle(ytitle)
            if not first_drawn:
                m.SetMaximum(max_val * 1.40 if max_val > 0 else 1.0)
                if not logy:
                    m.SetMinimum(0.0)
                m.Draw("HIST")
                first_drawn = True
            else:
                m.Draw("HIST SAME")
            legend.AddEntry(m, "{} {}".format(mc_label, flavor), "l")
            keep.append(m)
        if dh is not None:
            d = dh.Clone("{}_{}_data_flavor_cmp".format(dh.GetName(), safe_col(flavor)))
            d.SetDirectory(0)
            style_data_points(d, flavor)
            d.Draw("E1 SAME" if first_drawn else "E1")
            first_drawn = True
            legend.AddEntry(d, "{} {}".format(data_label, flavor), "lep")
            keep.append(d)

    legend.Draw()
    c._keep = keep + [legend]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_data_mc_stack(mc_hists_by_flavor, data_all_hist, out_dir, name, title, ytitle, formats,
                       data_label="Data", mc_label="MC", logy=False):
    """Draw MC flavor stack and overlay inclusive data as points."""
    if not mc_hists_by_flavor:
        return None
    c = ROOT.TCanvas("c_{}".format(name), "", 1050, 800)
    c.SetGrid()
    if logy:
        c.SetLogy()

    stack = ROOT.THStack("stack_{}".format(name), title)
    legend = ROOT.TLegend(0.58, 0.52, 0.90, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    keep = []

    for flavor, hist in mc_hists_by_flavor:
        h = hist.Clone("{}_mc_stack".format(hist.GetName()))
        h.SetDirectory(0)
        keep.append(h)
        style_mc_line(h, flavor, fill=True)
        stack.Add(h, "HIST")
        legend.AddEntry(h, "{} {}".format(mc_label, flavor), "f")

    stack.Draw("HIST")
    if mc_hists_by_flavor:
        stack.GetXaxis().SetTitle(mc_hists_by_flavor[0][1].GetXaxis().GetTitle())
    stack.GetYaxis().SetTitle(ytitle)

    max_y = stack.GetMaximum()
    if data_all_hist is not None:
        max_y = max(max_y, data_all_hist.GetMaximum())
    if max_y > 0:
        stack.SetMaximum(max_y * 1.35)
        if not logy:
            stack.SetMinimum(0.0)

    if data_all_hist is not None:
        d = data_all_hist.Clone("{}_data_stack_points".format(data_all_hist.GetName()))
        d.SetDirectory(0)
        keep.append(d)
        style_data_points(d, "All", marker=21)
        d.Draw("E1 SAME")
        legend.AddEntry(d, "{} All".format(data_label), "lep")

    legend.Draw()
    c._keep = keep + [stack, legend]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_data_mc_graph(data_graph, mc_graph, out_dir, name, title, formats,
                       data_label="Data", mc_label="MC", flavor="All"):
    if data_graph is None or mc_graph is None:
        return None
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    d = data_graph.Clone("{}_data_cmp".format(data_graph.GetName()))
    m = mc_graph.Clone("{}_mc_cmp".format(mc_graph.GetName()))
    style_mc_line(m, flavor, fill=False)
    style_data_points(d, flavor)
    m.SetTitle(title)
    m.GetYaxis().SetRangeUser(-1.0, 1.0)
    m.Draw("ALP")
    d.Draw("P SAME")
    xmin = m.GetXaxis().GetXmin()
    xmax = m.GetXaxis().GetXmax()
    line = ROOT.TLine(xmin, 0.0, xmax, 0.0)
    line.SetLineStyle(2)
    line.Draw("SAME")
    legend = ROOT.TLegend(0.58, 0.74, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.AddEntry(d, data_label, "lep")
    legend.AddEntry(m, mc_label, "l")
    legend.Draw()
    c._keep = [d, m, line, legend]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_pu_reweighting_summary(h_data, h_mc, h_mc_rw, out_dir, formats, data_label="Data", mc_label="MC"):
    mkdir(out_dir)
    c = ROOT.TCanvas("c_pu_reweighting_summary", "", 950, 750)
    c.SetGrid()
    hd = h_data.Clone("h_pu_data_draw")
    hm = h_mc.Clone("h_pu_mc_draw")
    hr = h_mc_rw.Clone("h_pu_mc_reweighted_draw")
    for h in (hd, hm, hr):
        h.SetDirectory(0)
        h.SetStats(False)
        if h.Integral() > 0:
            h.Scale(1.0 / h.Integral())
        h.GetXaxis().SetTitle("nPV")
        h.GetYaxis().SetTitle("Normalized events")
    style_data_points(hd, "All", marker=21)
    hm.SetLineColor(ROOT.kBlue + 1)
    hm.SetMarkerColor(ROOT.kBlue + 1)
    hm.SetLineWidth(2)
    hm.SetFillStyle(0)
    hr.SetLineColor(ROOT.kRed + 1)
    hr.SetMarkerColor(ROOT.kRed + 1)
    hr.SetLineWidth(2)
    hr.SetFillStyle(0)
    max_y = max(hd.GetMaximum(), hm.GetMaximum(), hr.GetMaximum())
    hd.SetMaximum(max_y * 1.35 if max_y > 0 else 1.0)
    hd.Draw("E1")
    hm.Draw("HIST SAME")
    hr.Draw("HIST SAME")
    legend = ROOT.TLegend(0.58, 0.72, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.AddEntry(hd, data_label, "lep")
    legend.AddEntry(hm, "{} before PU rw".format(mc_label), "l")
    legend.AddEntry(hr, "{} after PU rw".format(mc_label), "l")
    legend.Draw()
    c._keep = [hd, hm, hr, legend]
    save_canvas(c, out_dir, "npv_data_mc_before_after_pu_reweight", formats)
    return c

def draw_rho_npv_2d(hist, eta_bin, eta_min, eta_max, flavor, out_dir, name, formats, use_abs_eta=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 1200, 850)
    c.SetRightMargin(0.16)
    c.SetLeftMargin(0.12)
    c.SetBottomMargin(0.12)
    c.SetTopMargin(0.10)
    c.SetGrid()

    hist.SetStats(False)
    hist.GetXaxis().SetTitle("#rho [GeV]")
    hist.GetYaxis().SetTitle("PV_{npvsGood}")
    hist.GetZaxis().SetTitle("Events")
    hist.Draw("COLZ")

    if use_abs_eta:
        label = "#bf{|#eta| bin %s: %.3f < |#eta| < %.3f}" % (str(eta_bin), eta_min, eta_max)
    else:
        label = "#bf{etaBin %s: %.3f < #eta < %.3f}" % (str(eta_bin), eta_min, eta_max)

    flavor_label = "#bf{%s}" % flavor
    latex = ROOT.TLatex()
    latex.SetNDC(True)
    latex.SetTextFont(42)
    latex.SetTextSize(0.052)
    latex.DrawLatex(0.13, 0.82, label)
    latex.SetTextSize(0.046)
    latex.DrawLatex(0.13, 0.755, flavor_label)

    c._keep = [latex]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_rho_profile_npv(profile, eta_bin, eta_min, eta_max, flavor, out_dir, name, formats, use_abs_eta=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetRightMargin(0.06)
    c.SetLeftMargin(0.13)
    c.SetBottomMargin(0.12)
    c.SetTopMargin(0.11)
    c.SetGrid()

    profile.SetStats(False)
    profile.SetLineColor(COLORS.get(flavor, ROOT.kBlack))
    profile.SetMarkerColor(COLORS.get(flavor, ROOT.kBlack))
    profile.SetMarkerStyle(20)
    profile.SetMarkerSize(0.85)
    profile.SetLineWidth(2)
    profile.GetXaxis().SetTitle("PV_{npvsGood}")
    profile.GetYaxis().SetTitle("#LT#rho#GT [GeV]")

    max_y = profile.GetMaximum()
    if max_y > 0:
        profile.SetMaximum(max_y * 1.35)
        profile.SetMinimum(0.0)

    profile.Draw("E1")

    if use_abs_eta:
        label = "#bf{|#eta| bin %s: %.3f < |#eta| < %.3f}" % (str(eta_bin), eta_min, eta_max)
    else:
        label = "#bf{etaBin %s: %.3f < #eta < %.3f}" % (str(eta_bin), eta_min, eta_max)

    flavor_label = "#bf{%s}" % flavor
    latex = ROOT.TLatex()
    latex.SetNDC(True)
    latex.SetTextFont(42)
    latex.SetTextSize(0.052)
    latex.DrawLatex(0.13, 0.82, label)
    latex.SetTextSize(0.046)
    latex.DrawLatex(0.13, 0.755, flavor_label)

    c._keep = [latex]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_rho_profile_stack_npv(contrib_hists, all_profile, eta_bin, eta_min, eta_max, out_dir, name, formats, use_abs_eta=False):
    c = ROOT.TCanvas("c_{}".format(name), "", 1050, 800)
    c.SetRightMargin(0.06)
    c.SetLeftMargin(0.13)
    c.SetBottomMargin(0.12)
    c.SetTopMargin(0.10)
    c.SetGrid()

    stack = ROOT.THStack("stack_{}".format(name), "")
    legend = ROOT.TLegend(0.60, 0.54, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)

    keep = []
    for flavor, hist in contrib_hists:
        h = hist.Clone("{}_stack".format(hist.GetName()))
        keep.append(h)
        style_hist(h, flavor, marker=False, fill=True)
        stack.Add(h, "HIST")
        legend.AddEntry(h, flavor, "f")

    stack.Draw("HIST")
    stack.GetXaxis().SetTitle("PV_{npvsGood}")
    stack.GetYaxis().SetTitle("#LT#rho#GT contribution [GeV]")

    max_y = stack.GetMaximum()
    if all_profile is not None:
        max_y = max(max_y, all_profile.GetMaximum())
    if max_y > 0:
        stack.SetMaximum(max_y * 1.35)

    if all_profile is not None:
        p_all = all_profile.Clone("{}_all_overlay".format(all_profile.GetName()))
        keep.append(p_all)
        p_all.SetLineColor(ROOT.kBlack)
        p_all.SetMarkerColor(ROOT.kBlack)
        p_all.SetMarkerStyle(20)
        p_all.SetMarkerSize(0.85)
        p_all.SetLineWidth(2)
        p_all.Draw("E1 SAME")
        legend.AddEntry(p_all, "Inclusive #LT#rho#GT", "lep")

    if use_abs_eta:
        label = "#bf{|#eta| bin %s: %.3f < |#eta| < %.3f}" % (str(eta_bin), eta_min, eta_max)
    else:
        label = "#bf{etaBin %s: %.3f < #eta < %.3f}" % (str(eta_bin), eta_min, eta_max)

    latex = ROOT.TLatex()
    latex.SetNDC(True)
    latex.SetTextFont(42)
    latex.SetTextSize(0.052)
    latex.DrawLatex(0.13, 0.82, label)
    latex.SetTextSize(0.040)
    latex.DrawLatex(0.13, 0.755, "#bf{#LT#rho#GT contribution stack}")

    legend.Draw()
    c._keep = keep + [stack, legend, latex]
    save_canvas(c, out_dir, name, formats)
    return c


def make_asymmetry_graph(name, title, eta_info, values, errors=None):
    pos, neg = [], []
    for eta_bin, eta_min, eta_max, eta in eta_info:
        item = {"etaBin": eta_bin, "eta": eta, "absEta": abs(eta),
                "value": values.get(eta_bin, 0.0),
                "error": errors.get(eta_bin, 0.0) if errors is not None else 0.0}
        if eta > 0:
            pos.append(item)
        elif eta < 0:
            neg.append(item)
    points = []
    used_neg = set()
    for p in sorted(pos, key=lambda x: x["absEta"]):
        best_idx, best_dist = None, 1e9
        for i, m in enumerate(neg):
            if i in used_neg:
                continue
            dist = abs(p["absEta"] - m["absEta"])
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_idx is None:
            continue
        m = neg[best_idx]
        used_neg.add(best_idx)
        yp, ym = p["value"], m["value"]
        denom = yp + ym
        if abs(denom) < 1e-12:
            asym, err = 0.0, 0.0
        else:
            asym = (yp - ym) / denom
            sp, sm = p["error"], m["error"]
            dA_dyp = 2.0 * ym / (denom * denom)
            dA_dym = -2.0 * yp / (denom * denom)
            err = math.sqrt((dA_dyp * sp) ** 2 + (dA_dym * sm) ** 2)
        points.append((p["absEta"], asym, err))
    graph = ROOT.TGraphErrors(len(points))
    graph.SetName(name)
    graph.SetTitle(title)
    for i, (x, y, ey) in enumerate(points):
        graph.SetPoint(i, x, y)
        graph.SetPointError(i, 0.0, ey)
    graph.GetXaxis().SetTitle("|#eta|")
    graph.GetYaxis().SetTitle("(Y_{+} - Y_{-}) / (Y_{+} + Y_{-})")
    return graph


def draw_asymmetry(graph, flavor, out_dir, name, formats):
    c = ROOT.TCanvas("c_{}".format(name), "", 950, 750)
    c.SetGrid()
    color = COLORS.get(flavor, ROOT.kBlack)
    graph.SetLineColor(color)
    graph.SetMarkerColor(color)
    graph.SetMarkerStyle(20)
    graph.SetMarkerSize(2)
    graph.SetLineWidth(2)
    graph.Draw("AP")
    graph.GetYaxis().SetRangeUser(-1.0, 1.0)
    xmin = graph.GetXaxis().GetXmin()
    xmax = graph.GetXaxis().GetXmax()
    line = ROOT.TLine(xmin, 0.0, xmax, 0.0)
    line.SetLineStyle(2)
    line.Draw("SAME")
    c._keep = [line]
    save_canvas(c, out_dir, name, formats)
    return c


def values_errors_from_hist(hist, eta_info):
    """Return etaBin -> bin content/error from an eta-axis histogram/profile."""
    _, ordered_eta_info = make_eta_display_edges(eta_info)
    values, errors = {}, {}
    for ibin, (eta_bin, _, _, _) in enumerate(ordered_eta_info, start=1):
        values[eta_bin] = hist.GetBinContent(ibin)
        errors[eta_bin] = hist.GetBinError(ibin)
    return values, errors


def collect_geometry(tree, args, branches):
    """Small setup scan to discover eta/phi geometry for variable-bin axes."""
    eta_branch = branches["eta"]
    eta_min_branch = branches["eta_min"]
    eta_max_branch = branches["eta_max"]
    eta_bin_branch = branches["eta_bin"]
    phi_branch = branches["phi"]
    phi_min_branch = branches["phi_min"]
    phi_max_branch = branches["phi_max"]
    phi_bin_branch = branches["phi_bin"]
    dphi_branch = branches["dphi"]

    eta_geom = {}
    phi_geom = {}
    n_entries = tree.GetEntries()
    if args.max_events > 0:
        n_entries = min(n_entries, args.max_events)
    n_scan = min(max(1, args.geometry_scan_events), n_entries)

    has_phi_min = branch_exists(tree, phi_min_branch)
    has_phi_max = branch_exists(tree, phi_max_branch)

    for iev in range(n_scan):
        tree.GetEntry(iev)
        eta_vals = list(get_vector(tree, eta_branch))
        eta_min_vals = list(get_vector(tree, eta_min_branch))
        eta_max_vals = list(get_vector(tree, eta_max_branch))
        eta_bin_vals = list(get_vector(tree, eta_bin_branch))
        phi_vals = list(get_vector(tree, phi_branch))
        phi_bin_vals = list(get_vector(tree, phi_bin_branch))
        dphi_vals = list(get_vector(tree, dphi_branch))
        if has_phi_min:
            phi_min_vals = list(get_vector(tree, phi_min_branch))
        else:
            phi_min_vals = [0.0] * len(phi_vals)
        if has_phi_max:
            phi_max_vals = list(get_vector(tree, phi_max_branch))
        else:
            phi_max_vals = [0.0] * len(phi_vals)

        n = min(len(eta_vals), len(eta_min_vals), len(eta_max_vals), len(eta_bin_vals), len(phi_vals), len(phi_bin_vals), len(dphi_vals))
        for i in range(n):
            eb = int(eta_bin_vals[i])
            pb = int(phi_bin_vals[i])
            if eb not in eta_geom:
                eta_geom[eb] = (float(eta_min_vals[i]), float(eta_max_vals[i]), float(eta_vals[i]))
            phi_geom.setdefault(eb, {})
            if pb not in phi_geom[eb]:
                phi_geom[eb][pb] = (
                    float(phi_min_vals[i]) if i < len(phi_min_vals) else 0.0,
                    float(phi_max_vals[i]) if i < len(phi_max_vals) else 0.0,
                    float(phi_vals[i]),
                    float(dphi_vals[i]),
                )

    eta_info = [(eb, vals[0], vals[1], vals[2]) for eb, vals in eta_geom.items()]
    eta_info.sort(key=lambda x: x[1])
    if not eta_info:
        raise RuntimeError("No eta-bin information collected during geometry scan.")

    return eta_info, phi_geom


def abs_eta_info_from_eta_info(eta_info):
    by_abs = {}
    for eb, eta_min, eta_max, eta in eta_info:
        key = abs(int(eb))
        amin = min(abs(float(eta_min)), abs(float(eta_max)))
        amax = max(abs(float(eta_min)), abs(float(eta_max)))
        if key not in by_abs:
            by_abs[key] = [amin, amax]
        else:
            by_abs[key][0] = min(by_abs[key][0], amin)
            by_abs[key][1] = max(by_abs[key][1], amax)
    return {k: tuple(v) for k, v in by_abs.items()}


def cpp_int_double_map_initializer(mapping):
    """Return a C++ std::map<int,double> initializer expression.

    Kept for backward compatibility/debugging.  The main RDF graph no longer
    embeds this expression directly inside Define(), because some ROOT/Cling
    versions have trouble JIT-parsing a large temporary std::map initializer in
    a Define expression.  See declare_eta_plot_x_switch_helper() below.
    """
    items = []
    for key in sorted(mapping):
        items.append("{{{}, {:.17g}}}".format(int(key), float(mapping[key])))
    return "std::map<int,double>{{{}}}".format(",".join(items))


def declare_eta_plot_x_switch_helper(mapping):
    """Declare a tiny Cling helper that maps etaBin keys to display-bin centers.

    This avoids putting a large std::map temporary directly in an RDataFrame
    Define expression, which can fail to JIT in ROOT 6.32/Cling.  A switch is
    simple C++ and is also faster than a map lookup for this small fixed table.
    """
    cases = []
    for key in sorted(mapping):
        cases.append("      case {key}: out.emplace_back({value:.17g}); break;".format(
            key=int(key), value=float(mapping[key])
        ))
    cpp_template = """
namespace pf_rdf_runtime {{
inline ROOT::VecOps::RVec<double> eta_plot_x_by_key(const ROOT::VecOps::RVec<int> &keys) {{
  ROOT::VecOps::RVec<double> out;
  out.reserve(keys.size());
  for (std::size_t i = 0; i < keys.size(); ++i) {{
    switch (static_cast<int>(keys[i])) {{
{cases}
      default: out.emplace_back(0.0); break;
    }}
  }}
  return out;
}}
}}
"""
    ROOT.gInterpreter.Declare(cpp_template.format(cases="\n".join(cases)))
    print("[info] declared eta display x-coordinate helper for {} eta bins".format(len(mapping)))


def declare_pu_weight_helper(weights, function_name="pu_weight_data_over_mc"):
    """Declare a small C++ switch that returns P_data(nPV)/P_MC(nPV)."""
    cases = []
    for npv in sorted(weights):
        cases.append("      case {npv}: return {w:.17g};".format(npv=int(npv), w=float(weights[npv])))
    cpp = """
namespace pf_rdf_runtime {{
inline double {fname}(int npv) {{
  switch (static_cast<int>(npv)) {{
{cases}
      default: return 0.0;
  }}
}}
}}
""".format(fname=function_name, cases="\n".join(cases))
    ROOT.gInterpreter.Declare(cpp)
    print("[info] declared PU-reweight helper '{}' for {} nPV bins".format(function_name, len(weights)))
    return "pf_rdf_runtime::{}(rdf_npv)".format(function_name)


def _make_hist_from_counts(name, title, counts, xmin=-0.5):
    nb = len(counts)
    hist = ROOT.TH1D(name, title, nb, xmin, xmin + nb)
    hist.Sumw2()
    hist.SetStats(False)
    for i, value in enumerate(counts, start=1):
        hist.SetBinContent(i, float(value))
        hist.SetBinError(i, math.sqrt(float(value)) if value >= 0.0 else 0.0)
    return hist


def compute_pu_weights(data_input, mc_input, tree_name, npv_branch, max_events, max_npv):
    """Compute normalized data/MC pileup weights from integer nPV distributions."""
    nbins = int(max_npv) + 1
    xmin = -0.5
    xmax = float(max_npv) + 0.5
    model_data = ("h_pu_data_for_weights", ";nPV;Events", nbins, xmin, xmax)
    model_mc = ("h_pu_mc_for_weights", ";nPV;Events", nbins, xmin, xmax)

    df_data = ROOT.RDataFrame(tree_name, data_input)
    df_mc = ROOT.RDataFrame(tree_name, mc_input)
    if max_events > 0:
        df_data = df_data.Filter("rdfentry_ < {}".format(int(max_events)), "max-events-data-pu")
        df_mc = df_mc.Filter("rdfentry_ < {}".format(int(max_events)), "max-events-mc-pu")
    df_data = df_data.Define("rdf_pu_npv", "static_cast<int>({})".format(npv_branch))
    df_mc = df_mc.Define("rdf_pu_npv", "static_cast<int>({})".format(npv_branch))
    h_data = df_data.Histo1D(model_data, "rdf_pu_npv").GetValue().Clone("h_pu_data_counts")
    h_mc = df_mc.Histo1D(model_mc, "rdf_pu_npv").GetValue().Clone("h_pu_mc_counts")
    h_data.SetDirectory(0)
    h_mc.SetDirectory(0)

    data_integral = h_data.Integral(1, nbins)
    mc_integral = h_mc.Integral(1, nbins)
    if data_integral <= 0.0:
        raise RuntimeError("Cannot compute PU weights: data nPV histogram is empty.")
    if mc_integral <= 0.0:
        raise RuntimeError("Cannot compute PU weights: MC nPV histogram is empty.")

    weights = {}
    mc_rw_counts = []
    for npv in range(nbins):
        ibin = npv + 1
        p_data = h_data.GetBinContent(ibin) / data_integral
        p_mc = h_mc.GetBinContent(ibin) / mc_integral
        weight = p_data / p_mc if p_mc > 0.0 else 0.0
        weights[npv] = weight
        mc_rw_counts.append(h_mc.GetBinContent(ibin) * weight)

    h_mc_rw = _make_hist_from_counts("h_pu_mc_reweighted_counts", ";nPV;Weighted events", mc_rw_counts, xmin=xmin)
    print("[info] computed PU weights from nPV=0..{} using normalized data/MC distributions".format(max_npv))
    return weights, h_data, h_mc, h_mc_rw


def book_profile1d(booked, df, model, xcol, ycol, wcol=None):
    result = df.Profile1D(model, xcol, ycol, wcol) if wcol else df.Profile1D(model, xcol, ycol)
    booked.append(result)
    return result


def book_histo2d(booked, df, model, xcol, ycol, wcol=None):
    result = df.Histo2D(model, xcol, ycol, wcol) if wcol else df.Histo2D(model, xcol, ycol)
    booked.append(result)
    return result


def run_booked_actions(booked):
    if not booked:
        return
    print("[info] booked {} RDataFrame actions; running event loop(s) now".format(len(booked)))
    try:
        ROOT.RDF.RunGraphs(booked)
    except Exception as exc:
        print("[warn] ROOT.RDF.RunGraphs failed or is unavailable: {}".format(exc))
        print("[warn] Falling back to triggering the first booked result; shared RDF actions should still run together.")
        booked[0].GetValue()


def add_rdf_progress_bar(df):
    """Attach ROOT's built-in RDF progress bar when this ROOT build provides it."""
    try:
        add_progress_bar = ROOT.RDF.Experimental.AddProgressBar
    except Exception:
        print("[warn] ROOT.RDF.Experimental.AddProgressBar is not available in this ROOT build; continuing without a progress bar.")
        return False

    try:
        add_progress_bar(df)
        print("[info] enabled ROOT RDataFrame progress bar")
        return True
    except Exception as first_exc:
        try:
            add_progress_bar(ROOT.RDF.AsRNode(df))
            print("[info] enabled ROOT RDataFrame progress bar")
            return True
        except Exception as second_exc:
            print("[warn] could not enable ROOT RDataFrame progress bar:")
            print("[warn]   direct call failed: {}".format(first_exc))
            print("[warn]   AsRNode call failed: {}".format(second_exc))
            return False


def main():
    parser = argparse.ArgumentParser(description="Make PFRhoStrip rho/n/sumPt/occupancy plots using ROOT.RDataFrame.")
    parser.add_argument("input", help="Input ROOT file. In Data/MC mode this is the data file.")
    parser.add_argument("--mc-input", default="",
                        help="Optional MC ROOT file. When set, Data/MC comparison plots are made using the positional input as data.")
    parser.add_argument("--data-label", default="Data", help="Legend label for the positional data input in Data/MC mode.")
    parser.add_argument("--mc-label", default="MC", help="Legend label for --mc-input in Data/MC mode.")
    parser.add_argument("--mc-pu-reweight", action="store_true",
                        help="Reweight MC events by P_data(nPV)/P_MC(nPV) before filling MC profiles/histograms.")
    parser.add_argument("--pu-reweight-max-npv", type=int, default=250,
                        help="Maximum integer nPV included in the PU-reweight lookup table; default includes 0..250.")
    parser.add_argument("--no-data-mc-comparison-plots", action="store_true",
                        help="With --mc-input, book MC but skip drawing extra Data/MC comparison plots.")
    parser.add_argument("-o", "--outdir", default="pf_rho_strip_plots_rdf", help="Output plot directory")
    parser.add_argument("--root-output", default="pf_rho_strip_plots_rdf.root", help="Output ROOT file")
    parser.add_argument("--tree", default="Events", help="Input tree name")
    parser.add_argument("--prefix", default=None, help="Branch prefix, e.g. PFRhoStrip")
    parser.add_argument("--nvtx-branch", default=None, help="nPV branch, e.g. PV_npvsGood")
    parser.add_argument("--formats", default="png,pdf", help="Comma-separated output formats")
    parser.add_argument("--max-events", type=int, default=-1, help="Maximum events")
    parser.add_argument("--progress", action="store_true",
                        help="Show ROOT's RDataFrame progress bar during the event loop when supported by this ROOT build.")
    parser.add_argument("--list-branches", action="store_true", help="List rho/PFRho branches and exit")
    parser.add_argument("--logy-stack", action="store_true", help="Use log-y for stack plots")
    parser.add_argument("--no-phi-plots", action="store_true", help="Disable phi plots inside each eta bin")
    parser.add_argument("--eta-bins-for-phi", default="", help="Comma-separated etaBin values for phi plots; default is all")
    parser.add_argument("--no-rho-npv-2d", action="store_true", help="Disable per-eta 2D plots of rho vs nPV")
    parser.add_argument("--no-rho-npv-profile", action="store_true", help="Disable TProfile plots of <rho> vs nPV")
    parser.add_argument("--rho-npv-signed-eta", action="store_true", help="Make rho-vs-nPV plots separately for signed etaBin instead of combining +/- into |eta| bins")
    parser.add_argument("--rho-npv-flavors", default="All,ChargedHadron,NeutralHadron,Photon,Electron,Muon",
                        help="Comma-separated flavors for rho-vs-nPV 2D plots")
    parser.add_argument("--rho-npv-bins-rho", type=int, default=80, help="Number of rho bins for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-rho-min", type=float, default=0.0, help="Minimum rho for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-rho-max", type=float, default=160.0, help="Maximum rho for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-bins-npv", type=int, default=125, help="Number of nPV bins for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-npv-min", type=float, default=0.0, help="Minimum nPV for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-npv-max", type=float, default=250.0, help="Maximum nPV for rho-vs-nPV plots")
    parser.add_argument("--threads", type=int, default=0,
                        help="Enable ROOT implicit MT. 0 means ROOT chooses all available threads; 1 disables implicit MT.")
    parser.add_argument("--geometry-scan-events", type=int, default=25,
                        help="Small setup scan used only to discover static eta/phi geometry for axis binning.")
    parser.add_argument("--cpp-helpers-header", default="",
                        help="Path to PFRhoStripRDFHelpers.h. Default: next to this Python script.")
    parser.add_argument("--cpp-helpers-source", default="",
                        help="Path to PFRhoStripRDFHelpers.cc, used only with --compile-cpp-helpers. Default: next to this Python script.")
    parser.add_argument("--cpp-helpers-library", default="",
                        help="Optional precompiled helper shared library to load, e.g. ./libPFRhoStripRDFHelpers.so.")
    parser.add_argument("--compile-cpp-helpers", action="store_true",
                        help="Compile PFRhoStripRDFHelpers.cc once with ROOT ACLiC before booking RDF actions.")
    args = parser.parse_args()

    ROOT.gROOT.SetBatch(True)
    ROOT.TH1.SetDefaultSumw2(True)

    def _enable_implicit_mt(nthreads=None):
        # Support both modern ROOT.EnableImplicitMT and older ROOT.ROOT.EnableImplicitMT spellings.
        target = getattr(ROOT, "EnableImplicitMT", None)
        if target is None:
            target = ROOT.ROOT.EnableImplicitMT
        if nthreads is None:
            target()
        else:
            target(int(nthreads))

    if args.threads != 1:
        if args.threads > 1:
            _enable_implicit_mt(args.threads)
            print("[info] enabled ROOT implicit MT with {} threads".format(args.threads))
        else:
            _enable_implicit_mt(None)
            print("[info] enabled ROOT implicit MT with ROOT default thread count")
    else:
        print("[info] implicit MT disabled (--threads 1)")

    load_cpp_helpers(args)

    formats = [x.strip().lstrip(".") for x in args.formats.split(",") if x.strip()]

    fin = ROOT.TFile.Open(args.input)
    if not fin or fin.IsZombie():
        raise RuntimeError("Could not open input file: {}".format(args.input))
    tree = fin.Get(args.tree)
    if not tree:
        raise RuntimeError("Could not find tree '{}' in {}".format(args.tree, args.input))

    if args.list_branches:
        print("[info] branches containing rho/PFRho:")
        for b in all_branch_names(tree):
            if "rho" in b.lower() or "pfrho" in b.lower():
                print("  " + b)
        return

    prefix = args.prefix
    if prefix is None:
        if branch_exists(tree, "PFRhoStrip_eta"):
            prefix = "PFRhoStrip"
        elif branch_exists(tree, "PFRhoStrp_eta"):
            prefix = "PFRhoStrp"
        else:
            raise RuntimeError("Could not autodetect prefix. Pass --prefix PFRhoStrip or --prefix PFRhoStrp.")

    eta_branch = "{}_eta".format(prefix)
    eta_min_branch = "{}_etaMin".format(prefix)
    eta_max_branch = "{}_etaMax".format(prefix)
    eta_bin_branch = "{}_etaBin".format(prefix)
    phi_branch = "{}_phi".format(prefix)
    phi_min_branch = "{}_phiMin".format(prefix)
    phi_max_branch = "{}_phiMax".format(prefix)
    phi_bin_branch = "{}_phiBin".format(prefix)
    dphi_branch = "{}_dPhi".format(prefix)

    required = [eta_branch, eta_min_branch, eta_max_branch, eta_bin_branch, phi_branch, phi_bin_branch, dphi_branch]
    missing = [b for b in required if not branch_exists(tree, b)]
    if missing:
        nearby = [b for b in all_branch_names(tree) if "rho" in b.lower() or "pfrho" in b.lower()]
        raise RuntimeError("Missing required branches: {}\nNearby rho branches:\n  {}".format(missing, "\n  ".join(nearby[:120])))

    # Resolve optional phi edges if present.
    branch_exists(tree, phi_min_branch)
    branch_exists(tree, phi_max_branch)

    # Use actual branch names after case-insensitive resolution.
    b_eta = resolve_branch_name(tree, eta_branch, True)
    b_eta_min = resolve_branch_name(tree, eta_min_branch, True)
    b_eta_max = resolve_branch_name(tree, eta_max_branch, True)
    b_eta_bin = resolve_branch_name(tree, eta_bin_branch, True)
    b_phi = resolve_branch_name(tree, phi_branch, True)
    b_phi_min = RESOLVED_BRANCHES.get(phi_min_branch, phi_min_branch)
    b_phi_max = RESOLVED_BRANCHES.get(phi_max_branch, phi_max_branch)
    b_phi_bin = resolve_branch_name(tree, phi_bin_branch, True)
    b_dphi = resolve_branch_name(tree, dphi_branch, True)

    available_flavors = []
    flavor_branches = {}
    for flavor, suffix in FLAVORS:
        rb, nb, sb = rho_branch(prefix, suffix), n_branch(prefix, suffix), sumpt_branch(prefix, suffix)
        if branch_exists(tree, rb) and branch_exists(tree, nb) and branch_exists(tree, sb):
            available_flavors.append((flavor, suffix))
            flavor_branches[flavor] = {
                "rho": resolve_branch_name(tree, rb, True),
                "n": resolve_branch_name(tree, nb, True),
                "sumPt": resolve_branch_name(tree, sb, True),
            }
        else:
            print("[warn] skipping {}: missing one of {}, {}, {}".format(flavor, rb, nb, sb))
    if not available_flavors:
        raise RuntimeError("No complete rho/n/sumPt flavor branch set found.")
    if ("All", "") not in available_flavors:
        raise RuntimeError("Missing All branches; needed for rho contribution stack.")
    stack_flavors = [(fl, suf) for fl, suf in STACK_FLAVORS if (fl, suf) in available_flavors]

    nvtx_branch = args.nvtx_branch
    if nvtx_branch is None:
        nvtx_branch = find_first_branch(tree, ["PV_npvsGood", "PV_npvs", "nPV", "nVertex", "Pileup_nTrueInt"])
        if nvtx_branch:
            print("[info] Using nPV branch: {}".format(nvtx_branch))
        else:
            print("[warn] No numeric nPV branch found. Only Inclusive category and no rho-vs-nPV output will be meaningful.")
    elif not branch_exists(tree, nvtx_branch):
        raise RuntimeError("Requested nPV branch does not exist: {}".format(nvtx_branch))

    actual_npv_branch = resolve_branch_name(tree, nvtx_branch, True) if nvtx_branch else None
    if actual_npv_branch:
        leaf = tree.GetLeaf(actual_npv_branch)
        if leaf:
            print("[info] Using nPV branch: {}  leaf type: {}".format(actual_npv_branch, leaf.ClassName()))

    branches = {
        "eta": eta_branch,
        "eta_min": eta_min_branch,
        "eta_max": eta_max_branch,
        "eta_bin": eta_bin_branch,
        "phi": phi_branch,
        "phi_min": phi_min_branch,
        "phi_max": phi_max_branch,
        "phi_bin": phi_bin_branch,
        "dphi": dphi_branch,
    }
    eta_info, phi_geom = collect_geometry(tree, args, branches)
    eta_edges, ordered_eta_info = make_eta_display_edges(eta_info)
    # For eta plots, emulate the original make_eta_hist behavior exactly:
    # fill the visual bin associated with each etaBin.  Do not use the physical
    # eta branch center as the TProfile x coordinate, because make_eta_display_edges
    # deliberately changes transition-region display edges to be non-overlapping;
    # some physical centers can then land in neighboring display bins, producing
    # gaps or swapped edge bins in the RDF output.
    eta_plot_x_by_key = {
        int(eta_bin): 0.5 * (float(eta_edges[i]) + float(eta_edges[i + 1]))
        for i, (eta_bin, _, _, _) in enumerate(ordered_eta_info)
    }
    eta_plot_x_lookup_expr = cpp_int_double_map_initializer(eta_plot_x_by_key)  # useful for debugging/printing
    declare_eta_plot_x_switch_helper(eta_plot_x_by_key)
    abs_eta_geom = abs_eta_info_from_eta_info(eta_info)
    fin.Close()

    selected_eta_bins_for_phi = None
    if args.eta_bins_for_phi.strip():
        selected_eta_bins_for_phi = set(int(x.strip()) for x in args.eta_bins_for_phi.split(",") if x.strip())

    selected_rho_npv_flavors = set(x.strip() for x in args.rho_npv_flavors.split(",") if x.strip())

    vertex_bins = [
        VertexBin("Inclusive", None, None, inclusive=True),
        VertexBin("0_20", 0, 20),
        VertexBin("20_40", 20, 40),
        VertexBin("40_60", 40, 60),
        VertexBin("60_80", 60, 80),
        VertexBin("80_100", 80, 100),
    ]
    quantities = ["rho", "n", "sumPt", "occupancy"]
    ytitles = {
        "rho": "#rho [GeV]",
        "rhoContribution": "#rho contribution [GeV]",
        "n": "mean No. Candidates per event",
        "sumPt": "mean #Sigma p_{T} per event",
        "occupancy": "mean occupied #phi-strip fraction",
    }

    compare_data_mc = bool(args.mc_input) and (not args.no_data_mc_comparison_plots)
    mc_weight_expr = None
    pu_summary_hists = None
    if args.mc_input and args.mc_pu_reweight:
        if not actual_npv_branch:
            raise RuntimeError("--mc-pu-reweight requires a numeric nPV branch; pass --nvtx-branch if autodetection failed.")
        print("[info] computing MC PU weights from data/MC nPV distributions")
        pu_weights, h_pu_data, h_pu_mc, h_pu_mc_rw = compute_pu_weights(
            args.input,
            args.mc_input,
            args.tree,
            actual_npv_branch,
            args.max_events,
            args.pu_reweight_max_npv,
        )
        mc_weight_expr = declare_pu_weight_helper(pu_weights, "pu_weight_data_over_mc")
        pu_summary_hists = (h_pu_data, h_pu_mc, h_pu_mc_rw)
        if "PU reweighted" not in args.mc_label:
            args.mc_label = args.mc_label + " PU reweighted"

    def book_dataset(input_path, tag, event_weight_expr=None):
        """Build and book the full RDF graph for one input file."""
        print("[info] building RDataFrame graph for {}: {}".format(tag, input_path))
        df_local = ROOT.RDataFrame(args.tree, input_path)
        if args.max_events > 0:
            # Use rdfentry_ instead of Range so this also works with implicit MT.
            df_local = df_local.Filter("rdfentry_ < {}".format(int(args.max_events)), "max-events-{}".format(tag))

        if actual_npv_branch:
            df_local = df_local.Define("rdf_npv", "static_cast<int>({})".format(actual_npv_branch))
        else:
            df_local = df_local.Define("rdf_npv", "-1")

        use_event_weight = event_weight_expr is not None
        if use_event_weight:
            df_local = df_local.Define("rdf_event_weight", event_weight_expr)

        # Common eta reductions. All of these return one value per event per etaBin.
        df_local = df_local.Define("rdf_eta_keys", "pf_rdf::eta_keys({})".format(b_eta_bin))
        df_local = df_local.Define("rdf_eta_x", "pf_rdf::eta_centers_by_key({}, {})".format(b_eta_bin, b_eta))
        df_local = df_local.Define("rdf_eta_x_plot", "pf_rdf_runtime::eta_plot_x_by_key(rdf_eta_keys)")
        df_local = df_local.Define("rdf_abs_eta_keys", "pf_rdf::abs_eta_keys({})".format(b_eta_bin))
        df_local = df_local.Define("rdf_abs_eta_x", "pf_rdf::abs_eta_centers_by_key({}, {})".format(b_eta_bin, b_eta))
        if use_event_weight:
            df_local = df_local.Define("rdf_eta_weight", "pf_rdf::fill_like(rdf_eta_keys, rdf_event_weight)")
            df_local = df_local.Define("rdf_abs_eta_weight", "pf_rdf::fill_like(rdf_abs_eta_keys, rdf_event_weight)")

        for flavor, _ in available_flavors:
            flc = safe_col(flavor)
            rb = flavor_branches[flavor]["rho"]
            nb = flavor_branches[flavor]["n"]
            sb = flavor_branches[flavor]["sumPt"]
            df_local = df_local.Define("rdf_eta_rho_{}".format(flc), "pf_rdf::eta_mean_by_key({}, {})".format(b_eta_bin, rb))
            df_local = df_local.Define("rdf_eta_n_{}".format(flc), "pf_rdf::eta_sum_by_key({}, {})".format(b_eta_bin, nb))
            df_local = df_local.Define("rdf_eta_sumPt_{}".format(flc), "pf_rdf::eta_sum_by_key({}, {})".format(b_eta_bin, sb))
            df_local = df_local.Define("rdf_eta_occupancy_{}".format(flc), "pf_rdf::eta_occupancy_by_key({}, {})".format(b_eta_bin, nb))
            df_local = df_local.Define("rdf_abs_rho_{}".format(flc), "pf_rdf::abs_eta_mean_by_key({}, {})".format(b_eta_bin, rb))

        for flavor, _ in stack_flavors:
            flc = safe_col(flavor)
            sb = flavor_branches[flavor]["sumPt"]
            df_local = df_local.Define(
                "rdf_eta_rhoContribution_{}".format(flc),
                "pf_rdf::eta_contrib_by_key({}, {}, {}, {})".format(
                    b_eta_bin,
                    flavor_branches["All"]["rho"],
                    flavor_branches["All"]["sumPt"],
                    sb,
                ),
            )
            df_local = df_local.Define(
                "rdf_abs_rhoContribution_{}".format(flc),
                "pf_rdf::abs_eta_contrib_by_key({}, {}, {}, {})".format(
                    b_eta_bin,
                    flavor_branches["All"]["rho"],
                    flavor_branches["All"]["sumPt"],
                    sb,
                ),
            )

        if args.progress and tag == "data":
            add_rdf_progress_bar(df_local)

        dfs_by_cat_local = {}
        for vb in vertex_bins:
            if vb.inclusive:
                dfs_by_cat_local[vb.name] = df_local
            else:
                dfs_by_cat_local[vb.name] = df_local.Filter(vb.filter_expression("rdf_npv"), "nPV category {} {}".format(vb.name, tag))

        booked_local = []
        eta_profiles_local = {vb.name: {q: {} for q in quantities} for vb in vertex_bins}
        eta_contrib_profiles_local = {vb.name: {} for vb in vertex_bins}
        phi_profiles_local = {vb.name: {} for vb in vertex_bins}
        phi_contrib_profiles_local = {vb.name: {} for vb in vertex_bins}
        h2_rho_vs_npv_local = {}
        prof_rho_vs_npv_local = {}
        prof_rho_contrib_vs_npv_local = {}

        tag_suffix = "" if tag == "data" else "_{}".format(safe_col(tag))

        # Book eta profiles. Each profile bin content is the event mean of the
        # per-event, per-eta quantity, matching the original Stat aggregation.
        for vb in vertex_bins:
            cat = vb.name
            df_cat = dfs_by_cat_local[cat]
            eta_wcol = "rdf_eta_weight" if use_event_weight else None
            for quantity in quantities:
                for flavor, _ in available_flavors:
                    flc = safe_col(flavor)
                    ycol = "rdf_eta_{}_{}".format(quantity, flc)
                    hname = "{}_eta_{}_{}_{}{}".format(prefix, quantity, flavor, cat, tag_suffix)
                    htitle = "{} {} vs #eta, {}, {};#eta;{}".format(prefix, quantity, flavor, cat, ytitles[quantity])
                    model = profile_model_variable(hname, htitle, eta_edges)
                    eta_profiles_local[cat][quantity][flavor] = book_profile1d(booked_local, df_cat, model, "rdf_eta_x_plot", ycol, eta_wcol)

            for flavor, _ in stack_flavors:
                flc = safe_col(flavor)
                ycol = "rdf_eta_rhoContribution_{}".format(flc)
                hname = "{}_eta_rhoContribution_{}_{}{}".format(prefix, flavor, cat, tag_suffix)
                htitle = "{} rho contribution vs #eta, {}, {};#eta;{}".format(prefix, flavor, cat, ytitles["rhoContribution"])
                model = profile_model_variable(hname, htitle, eta_edges)
                eta_contrib_profiles_local[cat][flavor] = book_profile1d(booked_local, df_cat, model, "rdf_eta_x_plot", ycol, eta_wcol)

        # Book phi profiles. These are many actions, but they are still evaluated by
        # RDataFrame in compiled code rather than Python event loops.
        if not args.no_phi_plots:
            eta_bins_to_plot = [eb for eb, _, _, _ in ordered_eta_info]
            if selected_eta_bins_for_phi is not None:
                eta_bins_to_plot = [eb for eb in eta_bins_to_plot if eb in selected_eta_bins_for_phi]

            for vb in vertex_bins:
                cat = vb.name
                df_cat = dfs_by_cat_local[cat]
                phi_profiles_local[cat] = {eb: {q: {} for q in quantities} for eb in eta_bins_to_plot}
                phi_contrib_profiles_local[cat] = {eb: {} for eb in eta_bins_to_plot}

                for eb in eta_bins_to_plot:
                    phi_info = [(pb, vals[0], vals[1], vals[2], vals[3]) for pb, vals in phi_geom.get(eb, {}).items()]
                    phi_edges, _ = make_phi_edges(phi_info)
                    eb_col = safe_col(eb)

                    xcol = "rdf_phi_x_eta_{}_{}_{}".format(eb_col, safe_col(cat), safe_col(tag))
                    df_phi_x = df_cat.Define(xcol, "pf_rdf::phi_x_for_eta({}, {}, {})".format(b_eta_bin, b_phi, int(eb)))
                    phi_wcol = None
                    if use_event_weight:
                        phi_wcol = "rdf_phi_weight_eta_{}_{}_{}".format(eb_col, safe_col(cat), safe_col(tag))
                        df_phi_x = df_phi_x.Define(phi_wcol, "pf_rdf::fill_like({}, rdf_event_weight)".format(xcol))

                    for quantity in quantities:
                        for flavor, _ in available_flavors:
                            flc = safe_col(flavor)
                            if quantity == "rho":
                                expr = "pf_rdf::rows_for_eta({}, {}, {})".format(b_eta_bin, flavor_branches[flavor]["rho"], int(eb))
                            elif quantity == "n":
                                expr = "pf_rdf::rows_for_eta({}, {}, {})".format(b_eta_bin, flavor_branches[flavor]["n"], int(eb))
                            elif quantity == "sumPt":
                                expr = "pf_rdf::rows_for_eta({}, {}, {})".format(b_eta_bin, flavor_branches[flavor]["sumPt"], int(eb))
                            elif quantity == "occupancy":
                                expr = "pf_rdf::occupancy_rows_for_eta({}, {}, {})".format(b_eta_bin, flavor_branches[flavor]["n"], int(eb))
                            else:
                                raise RuntimeError("Unexpected quantity: {}".format(quantity))

                            ycol = "rdf_phi_{}_{}_eta_{}_{}_{}".format(quantity, flc, eb_col, safe_col(cat), safe_col(tag))
                            df_phi = df_phi_x.Define(ycol, expr)
                            hname = "{}_phi_{}_{}_{}_{}{}".format(prefix, quantity, flavor, cat, safe_name(eb), tag_suffix)
                            htitle = "{} {} vs #phi, {}, etaBin {};#phi;{}".format(prefix, quantity, cat, eb, ytitles[quantity])
                            model = profile_model_variable(hname, htitle, phi_edges)
                            phi_profiles_local[cat][eb][quantity][flavor] = book_profile1d(booked_local, df_phi, model, xcol, ycol, phi_wcol)

                    for flavor, _ in stack_flavors:
                        flc = safe_col(flavor)
                        ycol = "rdf_phi_rhoContribution_{}_eta_{}_{}_{}".format(flc, eb_col, safe_col(cat), safe_col(tag))
                        expr = "pf_rdf::contrib_rows_for_eta({}, {}, {}, {}, {})".format(
                            b_eta_bin,
                            flavor_branches["All"]["rho"],
                            flavor_branches["All"]["sumPt"],
                            flavor_branches[flavor]["sumPt"],
                            int(eb),
                        )
                        df_phi = df_phi_x.Define(ycol, expr)
                        hname = "{}_phi_rhoContribution_{}_{}_{}{}".format(prefix, flavor, cat, safe_name(eb), tag_suffix)
                        htitle = "{} rho contribution vs #phi, {}, etaBin {};#phi;{}".format(prefix, cat, eb, ytitles["rhoContribution"])
                        model = profile_model_variable(hname, htitle, phi_edges)
                        phi_contrib_profiles_local[cat][eb][flavor] = book_profile1d(booked_local, df_phi, model, xcol, ycol, phi_wcol)

        # Book inclusive rho-vs-nPV histograms/profiles.
        if not args.no_rho_npv_2d and actual_npv_branch:
            if args.rho_npv_signed_eta:
                eta_keys_for_npv = [eb for eb, _, _, _ in ordered_eta_info]
                key_col = "rdf_eta_keys"
                label_local = "etaBin"
                value_prefix = "rdf_eta_rho"
                contrib_prefix = "rdf_eta_rhoContribution"
            else:
                eta_keys_for_npv = sorted(abs_eta_geom.keys())
                key_col = "rdf_abs_eta_keys"
                label_local = "absEtaBin"
                value_prefix = "rdf_abs_rho"
                contrib_prefix = "rdf_abs_rhoContribution"

            for flavor, _ in available_flavors:
                if flavor not in selected_rho_npv_flavors:
                    continue
                flc = safe_col(flavor)
                source_val_col = "{}_{}".format(value_prefix, flc)
                for eta_key in eta_keys_for_npv:
                    etac = safe_col(eta_key)
                    rho_sel_col = "rdf_rho_npv_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                    npv_vec_col = "rdf_npv_vec_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                    df_sel = df_local.Define(rho_sel_col, "pf_rdf::select_by_key({}, {}, {})".format(key_col, source_val_col, int(eta_key))) \
                                     .Define(npv_vec_col, "pf_rdf::fill_like({}, static_cast<double>(rdf_npv))".format(rho_sel_col))
                    wvec_col = None
                    if use_event_weight:
                        wvec_col = "rdf_weight_vec_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                        df_sel = df_sel.Define(wvec_col, "pf_rdf::fill_like({}, rdf_event_weight)".format(rho_sel_col))
                    hname = "{}_rho_vs_npvsGood_{}_{}_{}{}".format(prefix, flavor, label_local, safe_name(eta_key), tag_suffix)
                    htitle = "{};#rho [GeV];PV_{{npvsGood}};Events".format(hname)
                    h2model = (hname, htitle,
                               args.rho_npv_bins_rho, args.rho_npv_rho_min, args.rho_npv_rho_max,
                               args.rho_npv_bins_npv, args.rho_npv_npv_min, args.rho_npv_npv_max)
                    h2 = book_histo2d(booked_local, df_sel, h2model, rho_sel_col, npv_vec_col, wvec_col)
                    h2_rho_vs_npv_local.setdefault(flavor, {})[eta_key] = h2

                    pname = "{}_directProfile_meanRho_vs_npvsGood_{}_{}_{}{}".format(prefix, flavor, label_local, safe_name(eta_key), tag_suffix)
                    ptitle = ";PV_{npvsGood};#LT#rho#GT [GeV]"
                    pmodel = (pname, ptitle, args.rho_npv_bins_npv, args.rho_npv_npv_min, args.rho_npv_npv_max)
                    prof_rho_vs_npv_local.setdefault(flavor, {})[eta_key] = book_profile1d(booked_local, df_sel, pmodel, npv_vec_col, rho_sel_col, wvec_col)

            for flavor, _ in stack_flavors:
                if flavor not in selected_rho_npv_flavors:
                    continue
                flc = safe_col(flavor)
                source_val_col = "{}_{}".format(contrib_prefix, flc)
                for eta_key in eta_keys_for_npv:
                    etac = safe_col(eta_key)
                    contrib_sel_col = "rdf_rho_contrib_npv_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                    npv_vec_col = "rdf_npv_vec_contrib_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                    df_sel = df_local.Define(contrib_sel_col, "pf_rdf::select_by_key({}, {}, {})".format(key_col, source_val_col, int(eta_key))) \
                                     .Define(npv_vec_col, "pf_rdf::fill_like({}, static_cast<double>(rdf_npv))".format(contrib_sel_col))
                    wvec_col = None
                    if use_event_weight:
                        wvec_col = "rdf_weight_vec_contrib_{}_{}_{}_{}".format(flc, label_local, etac, safe_col(tag))
                        df_sel = df_sel.Define(wvec_col, "pf_rdf::fill_like({}, rdf_event_weight)".format(contrib_sel_col))
                    pname = "{}_directProfile_meanRhoContribution_vs_npvsGood_{}_{}_{}{}".format(prefix, flavor, label_local, safe_name(eta_key), tag_suffix)
                    ptitle = ";PV_{npvsGood};#LT#rho#GT contribution [GeV]"
                    pmodel = (pname, ptitle, args.rho_npv_bins_npv, args.rho_npv_npv_min, args.rho_npv_npv_max)
                    prof_rho_contrib_vs_npv_local.setdefault(flavor, {})[eta_key] = book_profile1d(booked_local, df_sel, pmodel, npv_vec_col, contrib_sel_col, wvec_col)

        return {
            "booked": booked_local,
            "eta_profiles": eta_profiles_local,
            "eta_contrib_profiles": eta_contrib_profiles_local,
            "phi_profiles": phi_profiles_local,
            "phi_contrib_profiles": phi_contrib_profiles_local,
            "h2_rho_vs_npv": h2_rho_vs_npv_local,
            "prof_rho_vs_npv": prof_rho_vs_npv_local,
            "prof_rho_contrib_vs_npv": prof_rho_contrib_vs_npv_local,
        }

    data_results = book_dataset(args.input, "data", None)
    mc_results = book_dataset(args.mc_input, "mc", mc_weight_expr) if args.mc_input else None

    all_booked = list(data_results["booked"])
    if mc_results is not None:
        all_booked.extend(mc_results["booked"])
    run_booked_actions(all_booked)

    # Backward-compatible aliases used by the output-writing block below.
    eta_profiles = data_results["eta_profiles"]
    eta_contrib_profiles = data_results["eta_contrib_profiles"]
    phi_profiles = data_results["phi_profiles"]
    phi_contrib_profiles = data_results["phi_contrib_profiles"]
    h2_rho_vs_npv = data_results["h2_rho_vs_npv"]
    prof_rho_vs_npv = data_results["prof_rho_vs_npv"]
    prof_rho_contrib_vs_npv = data_results["prof_rho_contrib_vs_npv"]

    print("[info] writing plots and ROOT objects")
    mkdir(args.outdir)
    fout = ROOT.TFile.Open(args.root_output, "RECREATE")

    if pu_summary_hists is not None:
        pu_dir = os.path.join(args.outdir, "pu_reweighting")
        draw_pu_reweighting_summary(pu_summary_hists[0], pu_summary_hists[1], pu_summary_hists[2],
                                    pu_dir, formats, args.data_label, args.mc_label)
        root_pu_dir = fout.mkdir("pu_reweighting")
        root_pu_dir.cd()
        for h in pu_summary_hists:
            h.Write()

    # Eta plots and asymmetries.
    for vb in vertex_bins:
        cat = vb.name
        cat_dir = os.path.join(args.outdir, cat)
        eta_dir = os.path.join(cat_dir, "eta")
        mkdir(eta_dir)
        fout.mkdir(cat)
        fout.cd(cat)
        root_eta_dir = fout.GetDirectory(cat).mkdir("eta")

        materialized_eta_hists = {q: {} for q in quantities}
        materialized_contrib_hists = {}

        for quantity in quantities:
            q_dir = os.path.join(eta_dir, quantity)
            mkdir(q_dir)
            root_eta_dir.cd()
            root_q_dir = root_eta_dir.mkdir(quantity)
            root_q_dir.cd()
            hists = {}
            for flavor, _ in available_flavors:
                profile = eta_profiles[cat][quantity][flavor].GetValue()
                hname = "{}_eta_{}_{}_{}_hist".format(prefix, quantity, flavor, cat)
                hist = profile_to_hist(profile, hname, profile.GetTitle())
                style_hist(hist, flavor)
                hists[flavor] = hist
                materialized_eta_hists[quantity][flavor] = hist
                profile.Write()
                hist.Write()
                draw_individual(hist, q_dir, "{}_vs_eta_{}".format(quantity, flavor), formats)

            mc_hists = {}
            if mc_results is not None:
                cmp_dir = os.path.join(q_dir, "data_mc")
                mkdir(cmp_dir)
                for flavor, _ in available_flavors:
                    mc_profile = mc_results["eta_profiles"][cat][quantity][flavor].GetValue()
                    mc_hname = "{}_eta_{}_{}_{}_mc_hist".format(prefix, quantity, flavor, cat)
                    mc_hist = profile_to_hist(mc_profile, mc_hname, mc_profile.GetTitle())
                    style_hist(mc_hist, flavor)
                    mc_hists[flavor] = mc_hist
                    mc_profile.Write()
                    mc_hist.Write()
                    if compare_data_mc:
                        draw_data_mc_hist(hists.get(flavor), mc_hist, cmp_dir,
                                          "{}_vs_eta_{}_data_mc".format(quantity, flavor),
                                          "{} {} vs #eta, {}, {} vs {}".format(prefix, quantity, cat, args.data_label, args.mc_label),
                                          ytitles[quantity], formats, args.data_label, args.mc_label, flavor)

            overlay_inputs = [(fl, hists[fl]) for fl, _ in available_flavors if fl in hists]
            draw_overlay(overlay_inputs, q_dir, "{}_vs_eta_overlay".format(quantity),
                         "{} {} vs #eta overlay, {}".format(prefix, quantity, cat), ytitles[quantity], formats)
            if compare_data_mc and mc_hists:
                cmp_dir = os.path.join(q_dir, "data_mc")
                draw_data_mc_flavor_overlay(hists, mc_hists, [fl for fl, _ in available_flavors], cmp_dir,
                                            "{}_vs_eta_overlay_data_mc".format(quantity),
                                            "{} {} vs #eta overlay, {}, {} vs {}".format(prefix, quantity, cat, args.data_label, args.mc_label),
                                            ytitles[quantity], formats, args.data_label, args.mc_label)

            if quantity == "rho":
                contrib_hists = []
                for flavor, _ in stack_flavors:
                    profile = eta_contrib_profiles[cat][flavor].GetValue()
                    hname = "{}_eta_rhoContribution_{}_{}_hist".format(prefix, flavor, cat)
                    hist = profile_to_hist(profile, hname, profile.GetTitle())
                    style_hist(hist, flavor)
                    profile.Write()
                    hist.Write()
                    materialized_contrib_hists[flavor] = hist
                    contrib_hists.append((flavor, hist))
                draw_stack(contrib_hists, hists.get("All"), q_dir, "rho_vs_eta_stack_contribution",
                           "{} #rho contribution stack, {}".format(prefix, cat), ytitles["rho"], formats, args.logy_stack)
                if compare_data_mc and mc_results is not None:
                    cmp_dir = os.path.join(q_dir, "data_mc")
                    mkdir(cmp_dir)
                    mc_contrib_hists = []
                    for flavor, _ in stack_flavors:
                        mc_profile = mc_results["eta_contrib_profiles"][cat][flavor].GetValue()
                        mc_hist = profile_to_hist(mc_profile, "{}_eta_rhoContribution_{}_{}_mc_hist".format(prefix, flavor, cat), mc_profile.GetTitle())
                        style_hist(mc_hist, flavor)
                        mc_profile.Write()
                        mc_hist.Write()
                        mc_contrib_hists.append((flavor, mc_hist))
                    draw_data_mc_stack(mc_contrib_hists, hists.get("All"), cmp_dir, "rho_vs_eta_stack_contribution_data_mc",
                                       "{} #rho contribution stack, {}, {} vs {}".format(prefix, cat, args.data_label, args.mc_label),
                                       ytitles["rho"], formats, args.data_label, args.mc_label, args.logy_stack)
            else:
                stack_inputs = [(fl, hists[fl]) for fl, _ in stack_flavors if fl in hists]
                draw_stack(stack_inputs, hists.get("All"), q_dir, "{}_vs_eta_stack".format(quantity),
                           "{} {} flavor stack, {}".format(prefix, quantity, cat), ytitles[quantity], formats, args.logy_stack)
                if compare_data_mc and mc_hists:
                    cmp_dir = os.path.join(q_dir, "data_mc")
                    stack_mc_inputs = [(fl, mc_hists[fl]) for fl, _ in stack_flavors if fl in mc_hists]
                    draw_data_mc_stack(stack_mc_inputs, hists.get("All"), cmp_dir, "{}_vs_eta_stack_data_mc".format(quantity),
                                       "{} {} MC stack + data, {}, {} vs {}".format(prefix, quantity, cat, args.data_label, args.mc_label),
                                       ytitles[quantity], formats, args.data_label, args.mc_label, args.logy_stack)

        asym_dir = os.path.join(eta_dir, "asymmetry")
        mkdir(asym_dir)
        root_eta_dir.cd()
        root_asym_dir = root_eta_dir.mkdir("asymmetry")
        root_asym_dir.cd()
        for quantity in quantities:
            q_asym_dir = os.path.join(asym_dir, quantity)
            mkdir(q_asym_dir)
            for flavor, _ in available_flavors:
                hist = materialized_eta_hists[quantity][flavor]
                values, errors = values_errors_from_hist(hist, eta_info)
                gname = "{}_asym_eta_{}_{}_{}".format(prefix, quantity, flavor, cat)
                graph = make_asymmetry_graph(gname, gname, eta_info, values, errors)
                graph.Write()
                draw_asymmetry(graph, flavor, q_asym_dir, "asym_{}_{}".format(quantity, flavor), formats)
                if compare_data_mc and mc_results is not None:
                    cmp_dir = os.path.join(q_asym_dir, "data_mc")
                    mkdir(cmp_dir)
                    mc_profile = mc_results["eta_profiles"][cat][quantity][flavor].GetValue()
                    mc_hist = profile_to_hist(mc_profile, "{}_eta_{}_{}_{}_mc_hist_for_asym".format(prefix, quantity, flavor, cat), mc_profile.GetTitle())
                    mc_values, mc_errors = values_errors_from_hist(mc_hist, eta_info)
                    mc_gname = "{}_asym_eta_{}_{}_{}_mc".format(prefix, quantity, flavor, cat)
                    mc_graph = make_asymmetry_graph(mc_gname, mc_gname, eta_info, mc_values, mc_errors)
                    mc_graph.Write()
                    draw_data_mc_graph(graph, mc_graph, cmp_dir, "asym_{}_{}_data_mc".format(quantity, flavor),
                                       "{} asymmetry {}, {}, {} vs {}".format(prefix, quantity, cat, args.data_label, args.mc_label),
                                       formats, args.data_label, args.mc_label, flavor)

        if args.no_phi_plots:
            continue

        phi_base_dir = os.path.join(cat_dir, "phi")
        mkdir(phi_base_dir)
        fout.GetDirectory(cat).cd()
        root_phi_base = fout.GetDirectory(cat).mkdir("phi")
        for eb, emin, emax, eta_center in ordered_eta_info:
            if selected_eta_bins_for_phi is not None and eb not in selected_eta_bins_for_phi:
                continue
            phi_info = [(pb, vals[0], vals[1], vals[2], vals[3]) for pb, vals in phi_geom.get(eb, {}).items()]
            eta_label = "etaBin_{}_eta_{:.3f}".format(safe_name(eb), eta_center)
            eta_phi_dir = os.path.join(phi_base_dir, eta_label)
            mkdir(eta_phi_dir)
            root_phi_base.cd()
            root_eta_phi_dir = root_phi_base.mkdir(eta_label)

            for quantity in quantities:
                q_dir = os.path.join(eta_phi_dir, quantity)
                mkdir(q_dir)
                root_eta_phi_dir.cd()
                root_q_phi_dir = root_eta_phi_dir.mkdir(quantity)
                root_q_phi_dir.cd()
                hists = {}
                for flavor, _ in available_flavors:
                    profile = phi_profiles[cat][eb][quantity][flavor].GetValue()
                    hname = "{}_phi_{}_{}_{}_{}_hist".format(prefix, quantity, flavor, cat, safe_name(eb))
                    hist = profile_to_hist(profile, hname, profile.GetTitle())
                    style_hist(hist, flavor)
                    hists[flavor] = hist
                    profile.Write()
                    hist.Write()
                    draw_individual(hist, q_dir, "{}_vs_phi_{}".format(quantity, flavor), formats)

                mc_hists = {}
                if mc_results is not None:
                    cmp_dir = os.path.join(q_dir, "data_mc")
                    mkdir(cmp_dir)
                    for flavor, _ in available_flavors:
                        mc_profile = mc_results["phi_profiles"][cat][eb][quantity][flavor].GetValue()
                        mc_hname = "{}_phi_{}_{}_{}_{}_mc_hist".format(prefix, quantity, flavor, cat, safe_name(eb))
                        mc_hist = profile_to_hist(mc_profile, mc_hname, mc_profile.GetTitle())
                        style_hist(mc_hist, flavor)
                        mc_hists[flavor] = mc_hist
                        mc_profile.Write()
                        mc_hist.Write()
                        if compare_data_mc:
                            draw_data_mc_hist(hists.get(flavor), mc_hist, cmp_dir,
                                              "{}_vs_phi_{}_data_mc".format(quantity, flavor),
                                              "{} {} vs #phi, {}, etaBin {}, {} vs {}".format(prefix, quantity, cat, eb, args.data_label, args.mc_label),
                                              ytitles[quantity], formats, args.data_label, args.mc_label, flavor)

                overlay_inputs = [(fl, hists[fl]) for fl, _ in available_flavors if fl in hists]
                draw_overlay(overlay_inputs, q_dir, "{}_vs_phi_overlay".format(quantity),
                             "{} {} vs #phi overlay, {}, etaBin {}".format(prefix, quantity, cat, eb), ytitles[quantity], formats)
                if compare_data_mc and mc_hists:
                    cmp_dir = os.path.join(q_dir, "data_mc")
                    draw_data_mc_flavor_overlay(hists, mc_hists, [fl for fl, _ in available_flavors], cmp_dir,
                                                "{}_vs_phi_overlay_data_mc".format(quantity),
                                                "{} {} vs #phi overlay, {}, etaBin {}, {} vs {}".format(prefix, quantity, cat, eb, args.data_label, args.mc_label),
                                                ytitles[quantity], formats, args.data_label, args.mc_label)

                if quantity == "rho":
                    contrib_hists = []
                    for flavor, _ in stack_flavors:
                        profile = phi_contrib_profiles[cat][eb][flavor].GetValue()
                        hname = "{}_phi_rhoContribution_{}_{}_{}_hist".format(prefix, flavor, cat, safe_name(eb))
                        hist = profile_to_hist(profile, hname, profile.GetTitle())
                        style_hist(hist, flavor)
                        profile.Write()
                        hist.Write()
                        contrib_hists.append((flavor, hist))
                    draw_stack(contrib_hists, hists.get("All"), q_dir, "rho_vs_phi_stack_contribution",
                               "{} #rho contribution stack, {}, etaBin {}".format(prefix, cat, eb), ytitles["rho"], formats, args.logy_stack)
                    if compare_data_mc and mc_results is not None:
                        cmp_dir = os.path.join(q_dir, "data_mc")
                        mkdir(cmp_dir)
                        mc_contrib_hists = []
                        for flavor, _ in stack_flavors:
                            mc_profile = mc_results["phi_contrib_profiles"][cat][eb][flavor].GetValue()
                            mc_hist = profile_to_hist(mc_profile, "{}_phi_rhoContribution_{}_{}_{}_mc_hist".format(prefix, flavor, cat, safe_name(eb)), mc_profile.GetTitle())
                            style_hist(mc_hist, flavor)
                            mc_profile.Write()
                            mc_hist.Write()
                            mc_contrib_hists.append((flavor, mc_hist))
                        draw_data_mc_stack(mc_contrib_hists, hists.get("All"), cmp_dir, "rho_vs_phi_stack_contribution_data_mc",
                                           "{} #rho contribution stack, {}, etaBin {}, {} vs {}".format(prefix, cat, eb, args.data_label, args.mc_label),
                                           ytitles["rho"], formats, args.data_label, args.mc_label, args.logy_stack)
                else:
                    stack_inputs = [(fl, hists[fl]) for fl, _ in stack_flavors if fl in hists]
                    draw_stack(stack_inputs, hists.get("All"), q_dir, "{}_vs_phi_stack".format(quantity),
                               "{} {} flavor stack, {}, etaBin {}".format(prefix, quantity, cat, eb), ytitles[quantity], formats, args.logy_stack)
                    if compare_data_mc and mc_hists:
                        cmp_dir = os.path.join(q_dir, "data_mc")
                        stack_mc_inputs = [(fl, mc_hists[fl]) for fl, _ in stack_flavors if fl in mc_hists]
                        draw_data_mc_stack(stack_mc_inputs, hists.get("All"), cmp_dir, "{}_vs_phi_stack_data_mc".format(quantity),
                                           "{} {} MC stack + data, {}, etaBin {}, {} vs {}".format(prefix, quantity, cat, eb, args.data_label, args.mc_label),
                                           ytitles[quantity], formats, args.data_label, args.mc_label, args.logy_stack)

    # Rho-vs-nPV output.
    if not args.no_rho_npv_2d and actual_npv_branch:
        rho_npv_folder = "rho_vs_npvsGood_per_eta" if args.rho_npv_signed_eta else "rho_vs_npvsGood_per_absEta"
        rho_npv_dir = os.path.join(args.outdir, rho_npv_folder)
        mkdir(rho_npv_dir)
        root_rho_npv_dir = fout.mkdir(rho_npv_folder)

        use_abs_default = not args.rho_npv_signed_eta
        geom_lookup = ({eb: (emin, emax) for eb, emin, emax, _ in ordered_eta_info}
                       if args.rho_npv_signed_eta else abs_eta_geom)
        label = "etaBin" if args.rho_npv_signed_eta else "absEtaBin"

        for flavor in sorted(h2_rho_vs_npv.keys()):
            flavor_dir = os.path.join(rho_npv_dir, flavor)
            mkdir(flavor_dir)
            root_rho_npv_dir.cd()
            root_flavor_dir = root_rho_npv_dir.mkdir(flavor)
            for eta_key in sorted(h2_rho_vs_npv[flavor].keys()):
                eta_min, eta_max = geom_lookup.get(eta_key, (0.0, 0.0))
                root_flavor_dir.cd()
                hist = h2_rho_vs_npv[flavor][eta_key].GetValue()
                hist.Write()
                name = "rho_vs_npvsGood_{}_{}_{}".format(flavor, label, safe_name(eta_key))
                draw_rho_npv_2d(hist, eta_key, eta_min, eta_max, flavor, flavor_dir, name, formats, use_abs_eta=use_abs_default)
                if mc_results is not None:
                    mc_h2_ptr = mc_results["h2_rho_vs_npv"].get(flavor, {}).get(eta_key)
                    if mc_h2_ptr is not None:
                        mc_hist = mc_h2_ptr.GetValue()
                        mc_hist.Write()
                        mc_2d_dir = os.path.join(flavor_dir, "mc_2d")
                        mkdir(mc_2d_dir)
                        draw_rho_npv_2d(mc_hist, eta_key, eta_min, eta_max, flavor, mc_2d_dir,
                                        "rho_vs_npvsGood_{}_{}_{}_mc".format(flavor, label, safe_name(eta_key)),
                                        formats, use_abs_eta=use_abs_default)

                if not args.no_rho_npv_profile:
                    profile = prof_rho_vs_npv.get(flavor, {}).get(eta_key)
                    if profile is not None:
                        p = profile.GetValue()
                        p.Write()
                        profile_dir = os.path.join(flavor_dir, "profile_meanRho_vs_npvsGood")
                        mkdir(profile_dir)
                        profile_plot_name = "profile_meanRho_vs_npvsGood_{}_{}_{}".format(flavor, label, safe_name(eta_key))
                        draw_rho_profile_npv(p, eta_key, eta_min, eta_max, flavor, profile_dir,
                                             profile_plot_name, formats, use_abs_eta=use_abs_default)
                        if compare_data_mc and mc_results is not None:
                            mc_prof_ptr = mc_results["prof_rho_vs_npv"].get(flavor, {}).get(eta_key)
                            if mc_prof_ptr is not None:
                                mc_p = mc_prof_ptr.GetValue()
                                mc_p.Write()
                                cmp_dir = os.path.join(profile_dir, "data_mc")
                                mkdir(cmp_dir)
                                draw_data_mc_hist(p, mc_p, cmp_dir,
                                                  "profile_meanRho_vs_npvsGood_{}_{}_{}_data_mc".format(flavor, label, safe_name(eta_key)),
                                                  "{} <rho> vs nPV, {} {}, {} vs {}".format(prefix, label, eta_key, args.data_label, args.mc_label),
                                                  "#LT#rho#GT [GeV]", formats, args.data_label, args.mc_label, flavor)

        if not args.no_rho_npv_profile:
            stack_profile_dir = os.path.join(rho_npv_dir, "profile_meanRho_contribution_stack")
            mkdir(stack_profile_dir)
            root_rho_npv_dir.cd()
            root_stack_profile_dir = root_rho_npv_dir.mkdir("profile_meanRho_contribution_stack")

            eta_keys = set()
            if "All" in prof_rho_vs_npv:
                eta_keys.update(prof_rho_vs_npv["All"].keys())
            for flavor in prof_rho_contrib_vs_npv:
                eta_keys.update(prof_rho_contrib_vs_npv[flavor].keys())

            for eta_key in sorted(eta_keys):
                all_profile_ptr = prof_rho_vs_npv.get("All", {}).get(eta_key)
                if all_profile_ptr is None:
                    continue
                eta_min, eta_max = geom_lookup.get(eta_key, (0.0, 0.0))
                root_stack_profile_dir.cd()
                all_profile = all_profile_ptr.GetValue()
                all_profile.Write()
                contrib_hists = []
                for flavor, _ in stack_flavors:
                    prof_ptr = prof_rho_contrib_vs_npv.get(flavor, {}).get(eta_key)
                    if prof_ptr is None:
                        continue
                    prof = prof_ptr.GetValue()
                    prof.Write()
                    hist = profile_to_hist(prof, "{}_histForStack".format(prof.GetName()), prof.GetTitle())
                    hist.Write()
                    contrib_hists.append((flavor, hist))

                if contrib_hists:
                    plot_name = "profile_meanRho_contribution_stack_{}_{}".format(label, safe_name(eta_key))
                    draw_rho_profile_stack_npv(
                        contrib_hists,
                        all_profile,
                        eta_key,
                        eta_min,
                        eta_max,
                        stack_profile_dir,
                        plot_name,
                        formats,
                        use_abs_eta=use_abs_default,
                    )
                    if compare_data_mc and mc_results is not None:
                        mc_contrib_hists = []
                        for flavor, _ in stack_flavors:
                            mc_prof_ptr = mc_results["prof_rho_contrib_vs_npv"].get(flavor, {}).get(eta_key)
                            if mc_prof_ptr is None:
                                continue
                            mc_prof = mc_prof_ptr.GetValue()
                            mc_prof.Write()
                            mc_hist = profile_to_hist(mc_prof, "{}_histForStack_mc".format(mc_prof.GetName()), mc_prof.GetTitle())
                            mc_hist.Write()
                            mc_contrib_hists.append((flavor, mc_hist))
                        if mc_contrib_hists:
                            cmp_dir = os.path.join(stack_profile_dir, "data_mc")
                            mkdir(cmp_dir)
                            draw_data_mc_stack(mc_contrib_hists, all_profile, cmp_dir,
                                               "profile_meanRho_contribution_stack_{}_{}_data_mc".format(label, safe_name(eta_key)),
                                               "{} <rho> contribution stack vs nPV, {} {}, {} vs {}".format(prefix, label, eta_key, args.data_label, args.mc_label),
                                               "#LT#rho#GT contribution [GeV]", formats, args.data_label, args.mc_label, args.logy_stack)

    fout.Close()
    print("[done] plots written to {}".format(args.outdir))
    print("[done] ROOT objects written to {}".format(args.root_output))


if __name__ == "__main__":
    main()
