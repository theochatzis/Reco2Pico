#!/usr/bin/env python3
"""
make_pf_rho_strip_plots.py

PyROOT plotting script for PFRhoStrp/PFRhoStrip Nano/Pico branches.

Example usage:
python3 make_pf_rho_strip_plots.py pico.root \
  -o pf_rho_strip_plots \
  --root-output pf_rho_strip_plots.root \
  --prefix PFRhoStrp \
  --nvtx-branch PV_npvs

For each nPV category it makes:
  - rho vs eta for all PF candidates and each PF flavor
  - n vs eta for all PF candidates and each PF flavor
  - occupancy fraction vs eta for all PF candidates and each PF flavor
  - stacked flavor-contribution plots
  - eta+/eta- asymmetry plots

Definitions:
  rho:
    Uses PFRhoStrp_rho* branches directly. If your producer writes median rho per eta ring
    repeated on each phi strip row, this script averages duplicate phi rows in the same etaBin/event.

  n:
    Uses PFRhoStrp_n* branches. For each event and etaBin, it sums over all phi strips,
    so n vs eta is the total number of candidates in that eta ring per event.

  occupancy:
    Fraction of phi strips in an eta ring with n*>0 in each event.

  asymmetry:
    A(|eta|) = (Y(+|eta|) - Y(-|eta|)) / 0.5*(Y(+|eta|) + Y(-|eta|)).
"""




import argparse
import math
import os
from array import array
from collections import defaultdict
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
    #("Other", "Other"),
]

STACK_FLAVORS = [
    ("ChargedHadron", "ChargedHadron"),
    ("NeutralHadron", "NeutralHadron"),
    ("Photon", "Photon"),
    ("Electron", "Electron"),
    ("Muon", "Muon"),
    #("Other", "Other"),
]

COLORS = {
    "All": ROOT.kBlack,
    "ChargedHadron": ROOT.kRed + 1,
    "NeutralHadron": ROOT.kBlue + 1,
    "Photon": ROOT.kOrange + 1,
    "Electron": ROOT.kGreen + 2,
    "Muon": ROOT.kMagenta + 1,
    #"Other": ROOT.kGray + 2,
}

RESOLVED_BRANCHES = {}


@dataclass
class VertexBin:
    name: str
    low: Optional[int]
    high: Optional[int]
    inclusive: bool = False

    def accepts(self, npv: Optional[int]) -> bool:
        if self.inclusive:
            return True
        if npv is None:
            return False
        if self.low is None or self.high is None:
            return False
        if self.high == 100:
            return self.low <= npv <= self.high
        return self.low <= npv < self.high


class Stat:
    __slots__ = ("sum", "sumsq", "n")

    def __init__(self):
        self.sum = 0.0
        self.sumsq = 0.0
        self.n = 0

    def fill(self, x):
        x = float(x)
        self.sum += x
        self.sumsq += x * x
        self.n += 1

    @property
    def mean(self):
        return self.sum / self.n if self.n else 0.0

    @property
    def error(self):
        if self.n <= 1:
            return 0.0
        mean = self.mean
        var = max(self.sumsq / self.n - mean * mean, 0.0)
        return math.sqrt(var / self.n)


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def safe_name(x):
    return str(x).replace("-", "m").replace("+", "p").replace(".", "p")


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


def get_scalar_number(tree, branch_name, default=None):
    """Read scalar numeric branch robustly, including TLeafB Char_t/UChar_t."""
    if not branch_name:
        return default
    actual = RESOLVED_BRANCHES.get(branch_name, branch_name)
    try:
        leaf = tree.GetLeaf(actual)
        if leaf:
            return float(leaf.GetValue(0))
    except Exception:
        pass
    try:
        value = getattr(tree, actual)
    except Exception:
        return default
    try:
        if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
            if len(value) == 0:
                return default
            value = value[0]
    except Exception:
        pass
    if isinstance(value, bytes):
        if len(value) == 1:
            return float(value[0])
        try:
            value = value.decode()
        except Exception:
            return default
    if isinstance(value, str):
        if len(value) == 1:
            return float(ord(value))
        value = value.strip()
        if value == "":
            return default
    try:
        return float(value)
    except Exception:
        return default


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
        hist.SetMarkerSize(0.75)
    if fill:
        hist.SetFillColor(color)
        hist.SetFillStyle(1001)


def make_eta_hist(name, title, eta_info, values, errors=None, ytitle=""):
    edges = []
    for i, (_, eta_min, eta_max, _) in enumerate(eta_info):
        if i == 0:
            edges.append(float(eta_min))
        edges.append(float(eta_max))
    clean_edges = [edges[0]]
    for e in edges[1:]:
        if e <= clean_edges[-1]:
            e = clean_edges[-1] + 1e-5
        clean_edges.append(e)
    hist = ROOT.TH1D(name, title, len(clean_edges) - 1, array("d", clean_edges))
    hist.Sumw2()
    hist.SetStats(False)
    for ibin, (eta_bin, _, _, _) in enumerate(eta_info, start=1):
        hist.SetBinContent(ibin, values.get(eta_bin, 0.0))
        if errors is not None:
            hist.SetBinError(ibin, errors.get(eta_bin, 0.0))
    hist.GetXaxis().SetTitle("#eta")
    hist.GetYaxis().SetTitle(ytitle)
    return hist


def make_phi_hist(name, title, phi_info, values, errors=None, ytitle=""):
    if not phi_info:
        hist = ROOT.TH1D(name, title, 1, -math.pi, math.pi)
        return hist
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
        hist = ROOT.TH1D(name, title, len(clean_edges) - 1, array("d", clean_edges))
    else:
        ordered = sorted(phi_info, key=lambda x: x[3])
        hist = ROOT.TH1D(name, title, max(len(ordered), 1), -math.pi, math.pi)
    hist.Sumw2()
    hist.SetStats(False)
    hist.GetXaxis().SetTitle("#phi")
    hist.GetYaxis().SetTitle(ytitle)
    for phi_bin, _, _, phi, _ in ordered:
        ibin = hist.FindBin(float(phi))
        ibin = max(1, min(hist.GetNbinsX(), ibin))
        hist.SetBinContent(ibin, values.get(phi_bin, 0.0))
        if errors is not None:
            hist.SetBinError(ibin, errors.get(phi_bin, 0.0))
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



def draw_rho_npv_2d(hist, eta_bin, eta_min, eta_max, flavor, out_dir, name, formats, use_abs_eta=False):
    """Draw a 2D rho-vs-nPV histogram with bold eta-bin label."""
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
    # Put the eta-bin annotation inside the plotting area, large and bold.
    latex.SetTextSize(0.052)
    latex.DrawLatex(0.13, 0.82, label)
    latex.SetTextSize(0.046)
    latex.DrawLatex(0.13, 0.755, flavor_label)

    c._keep = [latex]
    save_canvas(c, out_dir, name, formats)
    return c


def draw_rho_profile_npv(profile, eta_bin, eta_min, eta_max, flavor, out_dir, name, formats, use_abs_eta=False):
    """Draw TProfile: <rho> as a function of PV_npvsGood."""
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
    # Put the eta-bin annotation inside the plotting area, large and bold.
    latex.SetTextSize(0.052)
    latex.DrawLatex(0.13, 0.82, label)
    latex.SetTextSize(0.046)
    latex.DrawLatex(0.13, 0.755, flavor_label)

    c._keep = [latex]
    save_canvas(c, out_dir, name, formats)
    return c


def profile_to_hist(profile, name):
    """Convert a TProfile to a TH1D so it can be put in a THStack."""
    nb = profile.GetNbinsX()
    xmin = profile.GetXaxis().GetXmin()
    xmax = profile.GetXaxis().GetXmax()

    hist = ROOT.TH1D(name, profile.GetTitle(), nb, xmin, xmax)
    hist.Sumw2()
    hist.SetStats(False)
    hist.GetXaxis().SetTitle(profile.GetXaxis().GetTitle())
    hist.GetYaxis().SetTitle(profile.GetYaxis().GetTitle())

    for ibin in range(1, nb + 1):
        hist.SetBinContent(ibin, profile.GetBinContent(ibin))
        hist.SetBinError(ibin, profile.GetBinError(ibin))

    return hist


def draw_rho_profile_stack_npv(contrib_hists, all_profile, eta_bin, eta_min, eta_max,
                               out_dir, name, formats, use_abs_eta=False):
    """Draw stacked <rho contribution> vs nPV profiles with inclusive <rho> overlaid."""
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
    graph.SetMarkerSize(0.85)
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


def values_errors_from_stats(stat_map):
    values = {k: st.mean for k, st in stat_map.items()}
    errors = {k: st.error for k, st in stat_map.items()}
    return values, errors


def main():
    parser = argparse.ArgumentParser(description="Make PFRhoStrip rho/n/sumPt/occupancy plots.")
    parser.add_argument("input", help="Input ROOT file")
    parser.add_argument("-o", "--outdir", default="pf_rho_strip_plots", help="Output plot directory")
    parser.add_argument("--root-output", default="pf_rho_strip_plots.root", help="Output ROOT file")
    parser.add_argument("--tree", default="Events", help="Input tree name")
    parser.add_argument("--prefix", default=None, help="Branch prefix, e.g. PFRhoStrip")
    parser.add_argument("--nvtx-branch", default=None, help="nPV branch, e.g. PV_npvsGood")
    parser.add_argument("--formats", default="png,pdf", help="Comma-separated output formats")
    parser.add_argument("--max-events", type=int, default=-1, help="Maximum events")
    parser.add_argument("--list-branches", action="store_true", help="List rho/PFRho branches and exit")
    parser.add_argument("--logy-stack", action="store_true", help="Use log-y for stack plots")
    parser.add_argument("--no-phi-plots", action="store_true", help="Disable phi plots inside each eta bin")
    parser.add_argument("--eta-bins-for-phi", default="", help="Comma-separated etaBin values for phi plots; default is all")
    parser.add_argument("--no-rho-npv-2d", action="store_true", help="Disable per-eta 2D plots of rho vs nPV")
    parser.add_argument("--no-rho-npv-profile", action="store_true", help="Disable TProfile plots of <rho> vs nPV made from the 2D rho-vs-nPV maps")
    parser.add_argument("--rho-npv-signed-eta", action="store_true", help="Make rho-vs-nPV plots separately for signed etaBin instead of combining +/- into |eta| bins")
    parser.add_argument("--rho-npv-flavors", default="All,ChargedHadron,NeutralHadron,Photon,Electron,Muon",
                        help="Comma-separated flavors for rho-vs-nPV 2D plots")
    parser.add_argument("--rho-npv-bins-rho", type=int, default=80, help="Number of rho bins for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-rho-min", type=float, default=0.0, help="Minimum rho for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-rho-max", type=float, default=160.0, help="Maximum rho for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-bins-npv", type=int, default=125, help="Number of nPV bins for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-npv-min", type=float, default=0.0, help="Minimum nPV for rho-vs-nPV plots")
    parser.add_argument("--rho-npv-npv-max", type=float, default=250.0, help="Maximum nPV for rho-vs-nPV plots")
    args = parser.parse_args()

    ROOT.gROOT.SetBatch(True)
    ROOT.TH1.SetDefaultSumw2(True)
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
            raise RuntimeError("Could not autodetect prefix. Pass --prefix PFRhoStrip.")

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

    branch_exists(tree, phi_min_branch)
    branch_exists(tree, phi_max_branch)

    available_flavors = []
    for flavor, suffix in FLAVORS:
        rb, nb, sb = rho_branch(prefix, suffix), n_branch(prefix, suffix), sumpt_branch(prefix, suffix)
        if branch_exists(tree, rb) and branch_exists(tree, nb) and branch_exists(tree, sb):
            available_flavors.append((flavor, suffix))
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
            print("[warn] No numeric nPV branch found. Only Inclusive category will be filled.")
    elif not branch_exists(tree, nvtx_branch):
        raise RuntimeError("Requested nPV branch does not exist: {}".format(nvtx_branch))
    if nvtx_branch:
        actual_npv_branch = RESOLVED_BRANCHES.get(nvtx_branch, nvtx_branch)
        leaf = tree.GetLeaf(actual_npv_branch)
        if leaf:
            print("[info] Using nPV branch: {}  leaf type: {}".format(actual_npv_branch, leaf.ClassName()))

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

    stats_eta = {vb.name: {q: {fl: defaultdict(Stat) for fl, _ in available_flavors} for q in quantities} for vb in vertex_bins}
    for vb in vertex_bins:
        stats_eta[vb.name]["rhoContribution"] = {fl: defaultdict(Stat) for fl, _ in stack_flavors}
    stats_phi = {vb.name: {q: {fl: defaultdict(lambda: defaultdict(Stat)) for fl, _ in available_flavors} for q in quantities} for vb in vertex_bins}
    for vb in vertex_bins:
        stats_phi[vb.name]["rhoContribution"] = {fl: defaultdict(lambda: defaultdict(Stat)) for fl, _ in stack_flavors}

    eta_geom = {}
    phi_geom = defaultdict(dict)
    selected_eta_bins_for_phi = None
    if args.eta_bins_for_phi.strip():
        selected_eta_bins_for_phi = set(int(x.strip()) for x in args.eta_bins_for_phi.split(",") if x.strip())

    selected_rho_npv_flavors = set(x.strip() for x in args.rho_npv_flavors.split(",") if x.strip())
    h2_rho_vs_npv = defaultdict(dict)  # h2_rho_vs_npv[flavor][etaBin or absEtaBin] = TH2D
    h2_rho_contrib_vs_npv = defaultdict(dict)  # contribution h2, same binning/keying as h2_rho_vs_npv

    # IMPORTANT:
    # The profile plots are filled directly with exact event values.
    # Do not derive the <rho> profiles from TH2::ProfileY, because ProfileY uses
    # the TH2 x-bin centers. With many exact-zero rho values, the first-bin center
    # biases the mean upward, and the flavor stack no longer closes to inclusive rho.
    prof_rho_vs_npv = defaultdict(dict)
    prof_rho_contrib_vs_npv = defaultdict(dict)

    abs_eta_geom = {}  # absEtaBin -> (absEtaMin, absEtaMax)

    def get_rho_npv_hist(flavor, eta_bin, eta_min, eta_max, use_abs_eta=False):
        if eta_bin in h2_rho_vs_npv[flavor]:
            return h2_rho_vs_npv[flavor][eta_bin]

        label = "absEtaBin" if use_abs_eta else "etaBin"
        hname = "{}_rho_vs_npvsGood_{}_{}_{}".format(prefix, flavor, label, safe_name(eta_bin))
        htitle = "{};#rho [GeV];PV_{{npvsGood}};Events".format(hname)
        hist = ROOT.TH2D(
            hname,
            htitle,
            args.rho_npv_bins_rho,
            args.rho_npv_rho_min,
            args.rho_npv_rho_max,
            args.rho_npv_bins_npv,
            args.rho_npv_npv_min,
            args.rho_npv_npv_max,
        )
        hist.Sumw2()
        hist._eta_min = eta_min
        hist._eta_max = eta_max
        hist._use_abs_eta = use_abs_eta
        h2_rho_vs_npv[flavor][eta_bin] = hist
        return hist

    def get_rho_contrib_npv_hist(flavor, eta_bin, eta_min, eta_max, use_abs_eta=False):
        if eta_bin in h2_rho_contrib_vs_npv[flavor]:
            return h2_rho_contrib_vs_npv[flavor][eta_bin]

        label = "absEtaBin" if use_abs_eta else "etaBin"
        hname = "{}_rhoContribution_vs_npvsGood_{}_{}_{}".format(prefix, flavor, label, safe_name(eta_bin))
        htitle = "{};#rho contribution [GeV];PV_{{npvsGood}};Events".format(hname)
        hist = ROOT.TH2D(
            hname,
            htitle,
            args.rho_npv_bins_rho,
            args.rho_npv_rho_min,
            args.rho_npv_rho_max,
            args.rho_npv_bins_npv,
            args.rho_npv_npv_min,
            args.rho_npv_npv_max,
        )
        hist.Sumw2()
        hist._eta_min = eta_min
        hist._eta_max = eta_max
        hist._use_abs_eta = use_abs_eta
        h2_rho_contrib_vs_npv[flavor][eta_bin] = hist
        return hist


    def get_rho_npv_profile(flavor, eta_bin, eta_min, eta_max, use_abs_eta=False):
        if eta_bin in prof_rho_vs_npv[flavor]:
            return prof_rho_vs_npv[flavor][eta_bin]

        label = "absEtaBin" if use_abs_eta else "etaBin"
        pname = "{}_directProfile_meanRho_vs_npvsGood_{}_{}_{}".format(prefix, flavor, label, safe_name(eta_bin))
        profile = ROOT.TProfile(
            pname,
            ";PV_{npvsGood};#LT#rho#GT [GeV]",
            args.rho_npv_bins_npv,
            args.rho_npv_npv_min,
            args.rho_npv_npv_max,
        )
        profile.Sumw2()
        profile._eta_min = eta_min
        profile._eta_max = eta_max
        profile._use_abs_eta = use_abs_eta
        prof_rho_vs_npv[flavor][eta_bin] = profile
        return profile

    def get_rho_contrib_npv_profile(flavor, eta_bin, eta_min, eta_max, use_abs_eta=False):
        if eta_bin in prof_rho_contrib_vs_npv[flavor]:
            return prof_rho_contrib_vs_npv[flavor][eta_bin]

        label = "absEtaBin" if use_abs_eta else "etaBin"
        pname = "{}_directProfile_meanRhoContribution_vs_npvsGood_{}_{}_{}".format(
            prefix, flavor, label, safe_name(eta_bin)
        )
        profile = ROOT.TProfile(
            pname,
            ";PV_{npvsGood};#LT#rho#GT contribution [GeV]",
            args.rho_npv_bins_npv,
            args.rho_npv_npv_min,
            args.rho_npv_npv_max,
        )
        profile.Sumw2()
        profile._eta_min = eta_min
        profile._eta_max = eta_max
        profile._use_abs_eta = use_abs_eta
        prof_rho_contrib_vs_npv[flavor][eta_bin] = profile
        return profile

    n_entries = tree.GetEntries()
    if args.max_events > 0:
        n_entries = min(n_entries, args.max_events)
    bad_npv_reads = 0

    for iev in range(n_entries):
        tree.GetEntry(iev)
        if iev and iev % 10000 == 0:
            print("[info] processed {}/{} events".format(iev, n_entries))
        npv_value = get_scalar_number(tree, nvtx_branch, default=None) if nvtx_branch else None
        npv = int(npv_value) if npv_value is not None else None
        if nvtx_branch and npv is None:
            bad_npv_reads += 1
            if bad_npv_reads <= 5:
                print("[warn] could not read numeric nPV from '{}'".format(nvtx_branch))
        active_categories = [vb.name for vb in vertex_bins if vb.accepts(npv)]
        if not active_categories:
            continue

        eta_vals = list(get_vector(tree, eta_branch))
        eta_min_vals = list(get_vector(tree, eta_min_branch))
        eta_max_vals = list(get_vector(tree, eta_max_branch))
        eta_bin_vals = list(get_vector(tree, eta_bin_branch))
        phi_vals = list(get_vector(tree, phi_branch))
        phi_bin_vals = list(get_vector(tree, phi_bin_branch))
        dphi_vals = list(get_vector(tree, dphi_branch))
        phi_min_vals = list(get_vector(tree, phi_min_branch)) if branch_exists(tree, phi_min_branch) else [0.0] * len(phi_vals)
        phi_max_vals = list(get_vector(tree, phi_max_branch)) if branch_exists(tree, phi_max_branch) else [0.0] * len(phi_vals)

        rows_by_eta = defaultdict(list)
        for i, eb_raw in enumerate(eta_bin_vals):
            eb, pb = int(eb_raw), int(phi_bin_vals[i])
            rows_by_eta[eb].append(i)
            if eb not in eta_geom:
                eta_geom[eb] = (float(eta_min_vals[i]), float(eta_max_vals[i]), float(eta_vals[i]))
            if pb not in phi_geom[eb]:
                phi_geom[eb][pb] = (float(phi_min_vals[i]), float(phi_max_vals[i]), float(phi_vals[i]), float(dphi_vals[i]))

        rho_arrays, n_arrays, sumpt_arrays = {}, {}, {}
        for flavor, suffix in available_flavors:
            rho_arrays[flavor] = list(get_vector(tree, rho_branch(prefix, suffix)))
            n_arrays[flavor] = list(get_vector(tree, n_branch(prefix, suffix)))
            sumpt_arrays[flavor] = list(get_vector(tree, sumpt_branch(prefix, suffix)))

        # For the rho-vs-nPV plots in |eta| bins, combine the +eta and -eta rings
        # into one event-level value per |eta| bin. This avoids filling two entries
        # per event when both detector sides are present.
        rho_npv_abs_values_this_event = defaultdict(lambda: defaultdict(list))
        rho_npv_abs_contribs_this_event = defaultdict(lambda: defaultdict(list))

        for eb, indices in rows_by_eta.items():
            if not indices:
                continue
            n_strips = len(indices)
            rho_all_eta = sum(float(rho_arrays["All"][i]) for i in indices) / float(n_strips)
            sumpt_all_eta = sum(float(sumpt_arrays["All"][i]) for i in indices)
            for flavor, _ in available_flavors:
                rho_val = sum(float(rho_arrays[flavor][i]) for i in indices) / float(n_strips)
                n_val = sum(float(n_arrays[flavor][i]) for i in indices)
                sumpt_val = sum(float(sumpt_arrays[flavor][i]) for i in indices)
                occ_val = sum(1.0 for i in indices if float(n_arrays[flavor][i]) > 0.0) / float(n_strips)
                for cat in active_categories:
                    stats_eta[cat]["rho"][flavor][eb].fill(rho_val)
                    stats_eta[cat]["n"][flavor][eb].fill(n_val)
                    stats_eta[cat]["sumPt"][flavor][eb].fill(sumpt_val)
                    stats_eta[cat]["occupancy"][flavor][eb].fill(occ_val)
            for flavor, _ in stack_flavors:
                sumpt_flav_eta = sum(float(sumpt_arrays[flavor][i]) for i in indices)
                contrib = rho_all_eta * sumpt_flav_eta / sumpt_all_eta if sumpt_all_eta > 0.0 else 0.0
                for cat in active_categories:
                    stats_eta[cat]["rhoContribution"][flavor][eb].fill(contrib)

            # Inclusive rho-vs-nPV maps.
            # By default combine +/- eta into one |eta| bin. With --rho-npv-signed-eta,
            # keep the old signed-eta behavior.
            if (not args.no_rho_npv_2d) and npv is not None:
                eta_min, eta_max, _eta_center = eta_geom[eb]

                if args.rho_npv_signed_eta:
                    for flavor, _ in available_flavors:
                        if flavor not in selected_rho_npv_flavors:
                            continue
                        rho_val = sum(float(rho_arrays[flavor][i]) for i in indices) / float(n_strips)
                        h2 = get_rho_npv_hist(flavor, eb, eta_min, eta_max, use_abs_eta=False)
                        h2.Fill(rho_val, float(npv))
                        prof = get_rho_npv_profile(flavor, eb, eta_min, eta_max, use_abs_eta=False)
                        prof.Fill(float(npv), rho_val)

                    for flavor, _ in stack_flavors:
                        if flavor not in selected_rho_npv_flavors:
                            continue
                        sumpt_flav_eta = sum(float(sumpt_arrays[flavor][i]) for i in indices)
                        contrib = rho_all_eta * sumpt_flav_eta / sumpt_all_eta if sumpt_all_eta > 0.0 else 0.0
                        h2c = get_rho_contrib_npv_hist(flavor, eb, eta_min, eta_max, use_abs_eta=False)
                        h2c.Fill(contrib, float(npv))
                        profc = get_rho_contrib_npv_profile(flavor, eb, eta_min, eta_max, use_abs_eta=False)
                        profc.Fill(float(npv), contrib)
                else:
                    abs_eb = abs(eb)
                    abs_eta_min = min(abs(eta_min), abs(eta_max))
                    abs_eta_max = max(abs(eta_min), abs(eta_max))
                    if abs_eb not in abs_eta_geom:
                        abs_eta_geom[abs_eb] = (abs_eta_min, abs_eta_max)

                    for flavor, _ in available_flavors:
                        if flavor not in selected_rho_npv_flavors:
                            continue
                        rho_val = sum(float(rho_arrays[flavor][i]) for i in indices) / float(n_strips)
                        rho_npv_abs_values_this_event[flavor][abs_eb].append(rho_val)

                    for flavor, _ in stack_flavors:
                        if flavor not in selected_rho_npv_flavors:
                            continue
                        sumpt_flav_eta = sum(float(sumpt_arrays[flavor][i]) for i in indices)
                        contrib = rho_all_eta * sumpt_flav_eta / sumpt_all_eta if sumpt_all_eta > 0.0 else 0.0
                        rho_npv_abs_contribs_this_event[flavor][abs_eb].append(contrib)

        # Fill one rho-vs-nPV point per event and per |eta| bin by averaging the +eta
        # and -eta ring values if both are present.
        if (not args.no_rho_npv_2d) and (not args.rho_npv_signed_eta) and npv is not None:
            for flavor, by_abs_eta in rho_npv_abs_values_this_event.items():
                for abs_eb, vals in by_abs_eta.items():
                    if not vals:
                        continue
                    abs_eta_min, abs_eta_max = abs_eta_geom.get(abs_eb, (0.0, 0.0))
                    rho_val_abs = sum(vals) / float(len(vals))
                    h2 = get_rho_npv_hist(flavor, abs_eb, abs_eta_min, abs_eta_max, use_abs_eta=True)
                    h2.Fill(rho_val_abs, float(npv))
                    prof = get_rho_npv_profile(flavor, abs_eb, abs_eta_min, abs_eta_max, use_abs_eta=True)
                    prof.Fill(float(npv), rho_val_abs)

            for flavor, by_abs_eta in rho_npv_abs_contribs_this_event.items():
                for abs_eb, vals in by_abs_eta.items():
                    if not vals:
                        continue
                    abs_eta_min, abs_eta_max = abs_eta_geom.get(abs_eb, (0.0, 0.0))
                    contrib_abs = sum(vals) / float(len(vals))
                    h2c = get_rho_contrib_npv_hist(flavor, abs_eb, abs_eta_min, abs_eta_max, use_abs_eta=True)
                    h2c.Fill(contrib_abs, float(npv))
                    profc = get_rho_contrib_npv_profile(flavor, abs_eb, abs_eta_min, abs_eta_max, use_abs_eta=True)
                    profc.Fill(float(npv), contrib_abs)

        if not args.no_phi_plots:
            for i, eb_raw in enumerate(eta_bin_vals):
                eb = int(eb_raw)
                if selected_eta_bins_for_phi is not None and eb not in selected_eta_bins_for_phi:
                    continue
                pb = int(phi_bin_vals[i])
                rho_all_phi = float(rho_arrays["All"][i])
                sumpt_all_phi = float(sumpt_arrays["All"][i])
                for flavor, _ in available_flavors:
                    rho_val = float(rho_arrays[flavor][i])
                    n_val = float(n_arrays[flavor][i])
                    sumpt_val = float(sumpt_arrays[flavor][i])
                    occ_val = 1.0 if n_val > 0.0 else 0.0
                    for cat in active_categories:
                        stats_phi[cat]["rho"][flavor][eb][pb].fill(rho_val)
                        stats_phi[cat]["n"][flavor][eb][pb].fill(n_val)
                        stats_phi[cat]["sumPt"][flavor][eb][pb].fill(sumpt_val)
                        stats_phi[cat]["occupancy"][flavor][eb][pb].fill(occ_val)
                for flavor, _ in stack_flavors:
                    sumpt_flav_phi = float(sumpt_arrays[flavor][i])
                    contrib = rho_all_phi * sumpt_flav_phi / sumpt_all_phi if sumpt_all_phi > 0.0 else 0.0
                    for cat in active_categories:
                        stats_phi[cat]["rhoContribution"][flavor][eb][pb].fill(contrib)

    print("[info] processed {} events".format(n_entries))
    if bad_npv_reads:
        print("[warn] nPV branch was unreadable in {} events; those events were Inclusive only.".format(bad_npv_reads))

    eta_info = [(eb, vals[0], vals[1], vals[2]) for eb, vals in eta_geom.items()]
    eta_info.sort(key=lambda x: x[1])
    if not eta_info:
        raise RuntimeError("No eta-bin information collected.")

    mkdir(args.outdir)
    fout = ROOT.TFile.Open(args.root_output, "RECREATE")

    for vb in vertex_bins:
        cat = vb.name
        cat_dir = os.path.join(args.outdir, cat)
        eta_dir = os.path.join(cat_dir, "eta")
        mkdir(eta_dir)
        fout.mkdir(cat)
        fout.cd(cat)
        root_eta_dir = fout.GetDirectory(cat).mkdir("eta")

        for quantity in quantities:
            q_dir = os.path.join(eta_dir, quantity)
            mkdir(q_dir)
            root_eta_dir.cd()
            root_q_dir = root_eta_dir.mkdir(quantity)
            root_q_dir.cd()
            hists = {}
            for flavor, _ in available_flavors:
                values, errors = values_errors_from_stats(stats_eta[cat][quantity][flavor])
                hname = "{}_eta_{}_{}_{}".format(prefix, quantity, flavor, cat)
                htitle = "{} {} vs #eta, {}, {}".format(prefix, quantity, flavor, cat)
                hist = make_eta_hist(hname, htitle, eta_info, values, errors, ytitles[quantity])
                style_hist(hist, flavor)
                hists[flavor] = hist
                hist.Write()
                draw_individual(hist, q_dir, "{}_vs_eta_{}".format(quantity, flavor), formats)
            overlay_inputs = [(fl, hists[fl]) for fl, _ in available_flavors if fl in hists]
            draw_overlay(overlay_inputs, q_dir, "{}_vs_eta_overlay".format(quantity),
                         "{} {} vs #eta overlay, {}".format(prefix, quantity, cat), ytitles[quantity], formats)
            if quantity == "rho":
                contrib_hists = []
                for flavor, _ in stack_flavors:
                    values, errors = values_errors_from_stats(stats_eta[cat]["rhoContribution"][flavor])
                    hname = "{}_eta_rhoContribution_{}_{}".format(prefix, flavor, cat)
                    hist = make_eta_hist(hname, hname, eta_info, values, errors, ytitles["rhoContribution"])
                    style_hist(hist, flavor)
                    hist.Write()
                    contrib_hists.append((flavor, hist))
                draw_stack(contrib_hists, hists.get("All"), q_dir, "rho_vs_eta_stack_contribution",
                           "{} #rho contribution stack, {}".format(prefix, cat), ytitles["rho"], formats, args.logy_stack)
            else:
                stack_inputs = [(fl, hists[fl]) for fl, _ in stack_flavors if fl in hists]
                draw_stack(stack_inputs, hists.get("All"), q_dir, "{}_vs_eta_stack".format(quantity),
                           "{} {} flavor stack, {}".format(prefix, quantity, cat), ytitles[quantity], formats, args.logy_stack)

        asym_dir = os.path.join(eta_dir, "asymmetry")
        mkdir(asym_dir)
        root_eta_dir.cd()
        root_asym_dir = root_eta_dir.mkdir("asymmetry")
        root_asym_dir.cd()
        for quantity in quantities:
            q_asym_dir = os.path.join(asym_dir, quantity)
            mkdir(q_asym_dir)
            for flavor, _ in available_flavors:
                values, errors = values_errors_from_stats(stats_eta[cat][quantity][flavor])
                gname = "{}_asym_eta_{}_{}_{}".format(prefix, quantity, flavor, cat)
                graph = make_asymmetry_graph(gname, gname, eta_info, values, errors)
                graph.Write()
                draw_asymmetry(graph, flavor, q_asym_dir, "asym_{}_{}".format(quantity, flavor), formats)

        if args.no_phi_plots:
            continue
        phi_base_dir = os.path.join(cat_dir, "phi")
        mkdir(phi_base_dir)
        fout.GetDirectory(cat).cd()
        root_phi_base = fout.GetDirectory(cat).mkdir("phi")
        for eb, emin, emax, eta_center in eta_info:
            if selected_eta_bins_for_phi is not None and eb not in selected_eta_bins_for_phi:
                continue
            phi_info = [(pb, vals[0], vals[1], vals[2], vals[3]) for pb, vals in phi_geom[eb].items()]
            phi_info.sort(key=lambda x: x[3])
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
                    values, errors = values_errors_from_stats(stats_phi[cat][quantity][flavor][eb])
                    hname = "{}_phi_{}_{}_{}_{}".format(prefix, quantity, flavor, cat, safe_name(eb))
                    hist = make_phi_hist(hname, hname, phi_info, values, errors, ytitles[quantity])
                    style_hist(hist, flavor)
                    hists[flavor] = hist
                    hist.Write()
                    draw_individual(hist, q_dir, "{}_vs_phi_{}".format(quantity, flavor), formats)
                overlay_inputs = [(fl, hists[fl]) for fl, _ in available_flavors if fl in hists]
                draw_overlay(overlay_inputs, q_dir, "{}_vs_phi_overlay".format(quantity),
                             "{} {} vs #phi overlay, {}, etaBin {}".format(prefix, quantity, cat, eb), ytitles[quantity], formats)
                if quantity == "rho":
                    contrib_hists = []
                    for flavor, _ in stack_flavors:
                        values, errors = values_errors_from_stats(stats_phi[cat]["rhoContribution"][flavor][eb])
                        hname = "{}_phi_rhoContribution_{}_{}_{}".format(prefix, flavor, cat, safe_name(eb))
                        hist = make_phi_hist(hname, hname, phi_info, values, errors, ytitles["rhoContribution"])
                        style_hist(hist, flavor)
                        hist.Write()
                        contrib_hists.append((flavor, hist))
                    draw_stack(contrib_hists, hists.get("All"), q_dir, "rho_vs_phi_stack_contribution",
                               "{} #rho contribution stack, {}, etaBin {}".format(prefix, cat, eb), ytitles["rho"], formats, args.logy_stack)
                else:
                    stack_inputs = [(fl, hists[fl]) for fl, _ in stack_flavors if fl in hists]
                    draw_stack(stack_inputs, hists.get("All"), q_dir, "{}_vs_phi_stack".format(quantity),
                               "{} {} flavor stack, {}, etaBin {}".format(prefix, quantity, cat, eb), ytitles[quantity], formats, args.logy_stack)

    # Write and draw inclusive rho-vs-nPV histograms.
    if not args.no_rho_npv_2d:
        rho_npv_folder = "rho_vs_npvsGood_per_eta" if args.rho_npv_signed_eta else "rho_vs_npvsGood_per_absEta"
        rho_npv_dir = os.path.join(args.outdir, rho_npv_folder)
        mkdir(rho_npv_dir)
        root_rho_npv_dir = fout.mkdir(rho_npv_folder)

        for flavor in sorted(h2_rho_vs_npv.keys()):
            flavor_dir = os.path.join(rho_npv_dir, flavor)
            mkdir(flavor_dir)
            root_rho_npv_dir.cd()
            root_flavor_dir = root_rho_npv_dir.mkdir(flavor)

            for eta_bin in sorted(h2_rho_vs_npv[flavor].keys()):
                hist = h2_rho_vs_npv[flavor][eta_bin]
                eta_min = getattr(hist, "_eta_min", 0.0)
                eta_max = getattr(hist, "_eta_max", 0.0)
                use_abs_eta = getattr(hist, "_use_abs_eta", False)

                root_flavor_dir.cd()
                hist.Write()

                label = "absEtaBin" if use_abs_eta else "etaBin"
                name = "rho_vs_npvsGood_{}_{}_{}".format(flavor, label, safe_name(eta_bin))
                draw_rho_npv_2d(hist, eta_bin, eta_min, eta_max, flavor, flavor_dir, name, formats, use_abs_eta=use_abs_eta)

                # Use the directly filled TProfile, not TH2::ProfileY.
                # TH2::ProfileY uses x-bin centers and biases exact-zero rho values upward.
                if not args.no_rho_npv_profile:
                    profile = prof_rho_vs_npv.get(flavor, {}).get(eta_bin)
                    if profile is not None:
                        profile.Write()

                        profile_dir = os.path.join(flavor_dir, "profile_meanRho_vs_npvsGood")
                        mkdir(profile_dir)
                        profile_plot_name = "profile_meanRho_vs_npvsGood_{}_{}_{}".format(flavor, label, safe_name(eta_bin))
                        draw_rho_profile_npv(profile, eta_bin, eta_min, eta_max, flavor, profile_dir,
                                             profile_plot_name, formats, use_abs_eta=use_abs_eta)

        # Stacked <rho> contribution profiles vs nPV, overlaid with the inclusive <rho> profile.
        if not args.no_rho_npv_profile:
            stack_profile_dir = os.path.join(rho_npv_dir, "profile_meanRho_contribution_stack")
            mkdir(stack_profile_dir)
            root_rho_npv_dir.cd()
            root_stack_profile_dir = root_rho_npv_dir.mkdir("profile_meanRho_contribution_stack")

            eta_keys = set()
            if "All" in h2_rho_vs_npv:
                eta_keys.update(h2_rho_vs_npv["All"].keys())
            for flavor in h2_rho_contrib_vs_npv:
                eta_keys.update(h2_rho_contrib_vs_npv[flavor].keys())

            for eta_bin in sorted(eta_keys):
                all_h2 = h2_rho_vs_npv.get("All", {}).get(eta_bin)
                if all_h2 is None:
                    continue

                eta_min = getattr(all_h2, "_eta_min", 0.0)
                eta_max = getattr(all_h2, "_eta_max", 0.0)
                use_abs_eta = getattr(all_h2, "_use_abs_eta", False)
                label = "absEtaBin" if use_abs_eta else "etaBin"

                root_stack_profile_dir.cd()

                all_profile = prof_rho_vs_npv.get("All", {}).get(eta_bin)
                if all_profile is None:
                    continue
                all_profile.Write()

                contrib_hists = []
                for flavor, _ in stack_flavors:
                    prof = prof_rho_contrib_vs_npv.get(flavor, {}).get(eta_bin)
                    if prof is None:
                        continue

                    prof.Write()

                    hist = profile_to_hist(prof, "{}_histForStack".format(prof.GetName()))
                    hist.Write()
                    contrib_hists.append((flavor, hist))

                if contrib_hists:
                    plot_name = "profile_meanRho_contribution_stack_{}_{}".format(label, safe_name(eta_bin))
                    draw_rho_profile_stack_npv(
                        contrib_hists,
                        all_profile,
                        eta_bin,
                        eta_min,
                        eta_max,
                        stack_profile_dir,
                        plot_name,
                        formats,
                        use_abs_eta=use_abs_eta,
                    )

    fout.Close()
    fin.Close()
    print("[done] plots written to {}".format(args.outdir))
    print("[done] ROOT objects written to {}".format(args.root_output))


if __name__ == "__main__":
    main()


