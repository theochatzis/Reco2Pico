#!/usr/bin/env python3
"""
TrueJES plots from the run_analysis.py output, every figure as .pdf and .png:

  response_vs_pt/ladder_sim_<region>  <pT/pT_GEN> vs pT_GEN, the simulation-level steps (SimJet ... SimPFJet)
  response_vs_pt/ladder_reco_<region> the same for the reconstructed steps (signal parts, JEC-corrected Puppi),
                                      with the ideal PF (SimPFJet) as the reference
  response_vs_pt/reco_<region>        the reconstructed jets raw and signal-only, with the ideal PF
  response_vs_pt/shared_sim_<region>  <E_shared/E_GEN> vs pT_GEN (only the energy descending from the gen jet),
  response_vs_pt/shared_reco_<region> simulation-level steps / reconstructed jets with the ideal PF
  response_vs_pt/puppijec_<region>    raw and JEC-corrected Puppi jets, full and signal part, with the ideal PF
  efficiency/efficiency_sim_<region>  matched fraction vs pT_GEN per step, simulation-level / reconstructed
  efficiency/efficiency_reco_<region>
  offset/offset_vs_pt_<region>[_<coll>]   <pT offset> (unattributed pt of the matched reconstructed jet) vs pT_GEN:
                                      the three collections overlaid, and per collection stacked by PF candidate type
  offset/offset_vs_eta_<ptbin>[_<coll>]   the same vs |eta_GEN| per gen-pt bin
  response_dist/<region>_<ptbin>_sim  response distributions per step in one gen-pt bin,
  response_dist/<region>_<ptbin>_reco simulation-level / reconstructed with the ideal PF
  composition/composition_<region>_<coll>  the fraction of the gen jet pT carried by each flavour
                                      component at the generator (charged hadrons, photons, neutral
                                      hadrons, leptons), in the ideal PF (charged from momentum,
                                      neutral and untrackable charged from deposits) and in the
                                      signal part of the reconstructed jet (by candidate type): how
                                      much of each component survives each step

With the pile-up truth of the classically mixed chain (run3_mix; skipped when the
histograms are empty):
  response_vs_pt/ladder_pileup_<region>  the ideal PF with pile-up (SimPFPUJet), after a perfect
                                      charged-hadron subtraction (SimPFPUCHSJet) and the raw
                                      reconstructed jets, with the ideal PF without pile-up
  response_vs_pt/pileup_pf_<region>   each ideal jet with pile-up against its reconstructed
  response_vs_pt/pileup_chs_<region>  counterpart: SimPFPUJet vs the raw PF jet, SimPFPUCHSJet vs
                                      the raw CHS jet, each with the signal part of the
                                      reconstructed jet and the ideal PF without pile-up
  offset/pileup_vs_pt_<region>_<coll> the offset split into the true in-time pile-up by candidate
                                      type and the residual (noise, out-of-time, calibration)
  offset/pileup_vs_eta_<ptbin>_<coll> the same vs |eta_GEN| per gen-pt bin

Every level keeps the same colour and marker in all figures (LEVEL_STYLE).

The ladder steps and regions are those of truejes_rdf_definition.py.
"""
import argparse
import os
import sys
from collections import OrderedDict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "SkimRDFAnalysisBase"))

from truejes_rdf_definition import ETA_REGIONS, GEN_TYPES, LEVELS, OFFSET_COLLECTIONS, OFFSET_TYPES, PT_BINS, SHARED_LEVELS, SIMPF_KINDS, pt_bin_label  # noqa: E402
from plotting import RootFileReader, hist_to_graph, plot_graphs  # noqa: E402
from plotting import plotters as _plotters, advanced as _advanced  # noqa: E402
from plotting.plotters import save_figure, draw_cms_label, apply_figure_margins  # noqa: E402
import matplotlib  # noqa: E402
import matplotlib.ticker  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mplhep as hep  # noqa: E402
from cycler import cycler  # noqa: E402

# The CMS style of the base package carries six colours; the ladder has seven
# rungs. Extend the cycle (same first six, so the colours of the earlier plots
# are unchanged) for every plotter of the base package and for this script.
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "*", "<", ">"]
_PALETTE = ["#5790fc", "#f89c20", "#e42536", "#964a8b", "#9c9ca1", "#7a21dd", "#2ca02c", "#8c564b", "#17becf", "#000000"]
_base_style = _plotters.use_hep_style


def use_hep_style():
    _base_style()
    plt.rcParams["axes.prop_cycle"] = cycler(color=_PALETTE)


_plotters.use_hep_style = use_hep_style
_advanced.use_hep_style = use_hep_style

# label, colour and marker of every level, the same in all figures
LEVEL_STYLE = OrderedDict([
    # level: (label, colour, marker); a raw jet and its signal part share the colour, not the marker
    ("Sim",          ("SimJet (entrance particles)",      "#5790fc", "o")),
    ("SimBoundary",  ("SimBoundaryJet (calo face)",       "#f89c20", "s")),
    ("SimCalo",      ("SimCaloJet (calo deposits)",       "#e42536", "^")),
    ("SimCaloCell",  ("SimCaloCellJet (calo cells)",      "#964a8b", "v")),
    ("SimPF",        ("SimPFJet (ideal PF)",              "#9c9ca1", "D")),
    ("PF",           ("PF jet (raw, with pile-up)",       "#7a21dd", "P")),
    ("PFSig",        ("PF jet, signal part",              "#7a21dd", "o")),
    ("CHS",          ("CHS jet (raw)",                    "#2ca02c", "X")),
    ("CHSSig",       ("CHS jet, signal part",             "#2ca02c", "s")),
    ("Puppi",        ("Puppi jet (raw)",                  "#8c564b", "*")),
    ("PuppiSig",     ("Puppi jet, signal part",           "#8c564b", "^")),
    ("PuppiCorr",    ("Puppi jet, JEC-corrected",         "#17becf", "<")),
    ("PuppiSigCorr", ("Puppi jet, signal part, corrected", "#000000", ">")),
    ("SimCaloCellPU", ("SimCaloCellPUJet (cells with pile-up)",  "#e377c2", "h")),
    ("SimPFPU",       ("SimPFPUJet (ideal PF with pile-up)",     "#bcbd22", "p")),
    ("SimPFPUCHS",    ("SimPFPUCHSJet (ideal PF, perfect CHS)",  "#ff7f0e", "H")),
])
LABEL = {k: v[0] for k, v in LEVEL_STYLE.items()}


def _levels(*names, **overrides):
    """OrderedDict level -> label for a figure; overrides rename a label"""
    return OrderedDict((n, overrides.get(n, LABEL[n])) for n in names)


def _style(levels):
    """colours and markers of a figure's levels, keyed by the label used in the legend"""
    colors = {label: LEVEL_STYLE[level][1] for level, label in levels.items()}
    markers = {label: LEVEL_STYLE[level][2] for level, label in levels.items()}
    return colors, markers


# the simulation-level steps, and the reconstructed steps with the ideal PF as the reference
SIM_LADDER = _levels("Sim", "SimBoundary", "SimCalo", "SimCaloCell", "SimPF")
RECO_LADDER = _levels("SimPF", "PFSig", "CHSSig", "PuppiSig", "PuppiCorr")
RECO = _levels("SimPF", "PF", "PFSig", "CHS", "CHSSig", "Puppi", "PuppiSig", "PuppiCorr")
SHARED_SIM = _levels("Sim", "SimBoundary", "SimCalo", "SimCaloCell", "SimPF")
SHARED_RECO = _levels("SimPF", "PF", "CHS", "Puppi", PF="PF jet", CHS="CHS jet", Puppi="Puppi jet")
PUPPI = _levels("Puppi", "PuppiCorr", "PuppiSig", "PuppiSigCorr", "SimPF", PuppiSig="Puppi jet, signal part (raw)")
PILEUP_LADDER = _levels("SimPF", "SimPFPUCHS", "SimPFPU", "SimCaloCellPU", "PF", "CHS", "Puppi")
PILEUP_PF = _levels("SimPF", "SimPFPU", "PF", "PFSig")
PILEUP_CHS = _levels("SimPF", "SimPFPUCHS", "CHS", "CHSSig")
RESIDUAL_COLOR = "#f0f0f0"  # the residual of the offset, hatched, next to the pile-up by candidate type
OFFSET_TYPE_LABELS = OrderedDict([
    ("chHad", "charged hadrons"), ("photon", "photons"), ("neuHad", "neutral hadrons"),
    ("hfHad", "HF hadrons"), ("hfEM", "HF EM"), ("other", "leptons, other"),
])
OFFSET_COLORS = ["#e42536", "#5790fc", "#f89c20", "#964a8b", "#7a21dd", "#9c9ca1"]
GEN_TYPE_LABELS = OrderedDict([("chHad", "charged hadrons"), ("photon", "photons"), ("neuHad", "neutral hadrons"), ("other", "leptons, other")])
GEN_TYPE_COLORS = ["#e42536", "#5790fc", "#f89c20", "#9c9ca1"]
SIMPF_KIND_LABELS = OrderedDict([("chargedTrack", "charged, from the momentum"), ("neutralDeposit", "neutral, from the deposit"), ("chargedDeposit", "charged untrackable, from the deposit")])
SIMPF_KIND_COLORS = ["#e42536", "#f89c20", "#964a8b"]
COLL_LABELS = {"PF": "PF jet (raw)", "CHS": "CHS jet (raw)", "Puppi": "Puppi jet (raw)"}
REGION_TEXT = {
    "Incl": r"$|\eta^{GEN}| < 5$", "HB": r"$|\eta^{GEN}| < 1.3$", "HE1": r"$1.3 < |\eta^{GEN}| < 2.5$",
    "HE2": r"$2.5 < |\eta^{GEN}| < 3.0$", "HF": r"$3.0 < |\eta^{GEN}| < 5.0$",
}


def _out(output_dir, subdir, name):
    """pdf and png targets of one figure"""
    d = os.path.join(output_dir, subdir)
    os.makedirs(d, exist_ok=True)
    return [os.path.join(d, name + ".pdf"), os.path.join(d, name + ".png")]


def _graph(reader, region, name, level):
    hist = reader.get("all/%s_%s_%s" % (name, level, region))
    return hist_to_graph(hist, drop_empty=True)


def response_plot(reader, region, levels, output, title, ylim=(0.3, 1.9), legend_loc=None, title_loc="upper left", require=None):
    """require: a level that must have entries, otherwise the figure is not made (pile-up truth figures on premixed samples)"""
    colors, markers = _style(levels)
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graph = _graph(reader, region, "Resp", level)
        except Exception as err:  # missing histogram
            print("skip", level, region, err)
            continue
        if len(graph.x) == 0:  # level not in this sample (e.g. the pile-up truth on a premixed one)
            if level == require:
                return
            continue
        graphs[label] = graph
    if not graphs:
        return
    plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel=r"$\langle p_T / p_T^{GEN} \rangle$",
                logx=True, reference_line=1.0, ylim=ylim, legend_outside=False, legend_fontsize="x-small",
                legend_loc=legend_loc, title_loc=title_loc,
                title=title, connect=True, cms_label="", data=False, markers=markers, colors=colors, hollow_markers=True, markersize=5.5)


def shared_plot(reader, region, levels, output, title):
    colors, markers = _style(levels)
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graphs[label] = _graph(reader, region, "RespShared", level)
        except Exception as err:
            print("skip", level, region, err)
    if graphs:
        plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel=r"$\langle E_{shared} / E^{GEN} \rangle$",
                    logx=True, reference_line=1.0, ylim=(0.3, 1.7), legend_outside=False, legend_fontsize="x-small",
                    legend_loc="upper right", title_loc="lower left",
                    title=title, connect=True, cms_label="", data=False, markers=markers, colors=colors, hollow_markers=True, markersize=5.5)


def _hist(reader, name):
    try:
        return reader.get("all/" + name)
    except Exception:
        return None


def offset_total_plot(reader, name_fmt, output, title, xlabel, logx):
    """<pT offset> of the three collections overlaid"""
    graphs = OrderedDict()
    for coll, label in COLL_LABELS.items():
        hist = _hist(reader, name_fmt % (coll, "total"))
        if hist is not None:
            graph = hist_to_graph(hist, drop_empty=True)
            if len(graph.y):
                graphs[label] = graph
    if graphs:
        ymax = max(float(np.nanmax(g.y)) for g in graphs.values())
        plot_graphs(graphs, output, xlabel=xlabel, ylabel=r"$\langle p_T^{\,offset} \rangle$ [GeV]",
                    logx=logx, ylim=(0, 1.9 * ymax), legend_outside=False, legend_fontsize="x-small", title=title,
                    connect=True, cms_label="", data=False, markers=MARKERS, hollow_markers=True, markersize=5.5)


def offset_composition_plot(reader, name_fmt, coll, output, title, xlabel, logx):
    """stacked composition of <pT offset> by PF candidate type for one collection"""
    use_hep_style()
    fig, ax = plt.subplots(figsize=(9, 7))
    bottom = None
    drawn = 0
    for (typ, label), color in zip(OFFSET_TYPE_LABELS.items(), OFFSET_COLORS):
        hist = _hist(reader, name_fmt % (coll, typ))
        if hist is None:
            continue
        values = np.where(np.isfinite(hist.values), hist.values, 0.0)
        if bottom is None:
            bottom = np.zeros_like(values)
        ax.bar(hist.centers, values, width=hist.widths, bottom=bottom, color=color, label=label, edgecolor=color, linewidth=0.5)
        bottom = bottom + values
        drawn += 1
    if not drawn:
        plt.close(fig)
        return
    total = _hist(reader, name_fmt % (coll, "total"))
    if total is not None:
        ax.errorbar(total.centers, total.values, yerr=total.errors, fmt="o", color="black", markersize=4, label="total")
    if logx:
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 20, 50, 100, 200])
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"$\langle p_T^{\,offset} \rangle$ [GeV]")
    ax.set_ylim(0, 2.2 * max(1e-3, float(np.nanmax(bottom))))
    ax.text(0.04, 0.96, "%s\n%s" % (COLL_LABELS[coll], title), transform=ax.transAxes, ha="left", va="top", fontsize="small")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], fontsize="x-small", loc="upper right", frameon=False)
    draw_cms_label(ax, cms_label="", data=False, com=13.6)
    apply_figure_margins(fig)
    save_figure(fig, output)
    plt.close(fig)


def pileup_composition_plot(reader, pu_fmt, res_fmt, tot_fmt, coll, output, title, xlabel, logx):
    """the offset of one collection split into the true in-time pile-up by candidate type and the residual"""
    total_res = _hist(reader, res_fmt % (coll, "total"))
    total_pu = _hist(reader, pu_fmt % (coll, "total"))
    if total_pu is None or total_res is None or not np.any(np.isfinite(total_pu.values) & (total_pu.values > 0)):
        return
    use_hep_style()
    fig, ax = plt.subplots(figsize=(9, 7))
    bottom = None
    for (typ, label), color in zip(OFFSET_TYPE_LABELS.items(), OFFSET_COLORS):
        hist = _hist(reader, pu_fmt % (coll, typ))
        if hist is None:
            continue
        values = np.where(np.isfinite(hist.values), hist.values, 0.0)
        if bottom is None:
            bottom = np.zeros_like(values)
        ax.bar(hist.centers, values, width=hist.widths, bottom=bottom, color=color, label="pile-up: " + label, edgecolor=color, linewidth=0.5)
        bottom = bottom + values
    res = np.where(np.isfinite(total_res.values), total_res.values, 0.0)
    ax.bar(total_res.centers, res, width=total_res.widths, bottom=bottom, color=RESIDUAL_COLOR, label="residual: noise, out-of-time, calibration",
           edgecolor="#555555", linewidth=0.5, hatch="//")
    bottom = bottom + res
    total = _hist(reader, tot_fmt % (coll, "total"))
    if total is not None:
        ax.errorbar(total.centers, total.values, yerr=total.errors, fmt="o", color="black", markersize=4, label="total offset")
    if logx:
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 20, 50, 100, 200])
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"$\langle p_T^{\,offset} \rangle$ [GeV]")
    ax.set_ylim(0, 2.2 * max(1e-3, float(np.nanmax(bottom))))
    ax.text(0.04, 0.96, "%s\n%s" % (COLL_LABELS[coll], title), transform=ax.transAxes, ha="left", va="top", fontsize="small")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], fontsize="x-small", loc="upper right", frameon=False)
    draw_cms_label(ax, cms_label="", data=False, com=13.6)
    apply_figure_margins(fig)
    save_figure(fig, output)
    plt.close(fig)


def _stack(ax, reader, fmt, items, colors, total_name):
    """stacked bars of TProfiles (fraction of the gen pt) vs gen pt; returns the top of the stack"""
    bottom = None
    for (key, label), color in zip(items.items(), colors):
        hist = _hist(reader, fmt % key)
        if hist is None:
            continue
        values = np.where(np.isfinite(hist.values), hist.values, 0.0)
        if bottom is None:
            bottom = np.zeros_like(values)
        ax.bar(hist.centers, values, width=hist.widths, bottom=bottom, color=color, edgecolor=color, linewidth=0.5, label=label)
        bottom = bottom + values
    total = _hist(reader, fmt % total_name)
    if total is not None:
        ax.errorbar(total.centers, total.values, yerr=total.errors, fmt="o", color="black", markersize=4, label="total")
    return bottom


def composition_plot(reader, region, coll, output, title):
    """gen jet / ideal PF / reconstructed signal part, each as the fraction of the gen pt by component"""
    gen = _hist(reader, "GenComp_total_%s" % region)
    if gen is None or not np.any(np.isfinite(gen.values) & (gen.values > 0)):
        return
    use_hep_style()
    fig, axes = plt.subplots(1, 3, figsize=(21, 6.5), sharey=True)
    panels = [
        ("generator particles", "GenComp_%s_" + region, GEN_TYPE_LABELS, GEN_TYPE_COLORS, "total"),
        ("ideal particle flow (SimPFJet)", "SimPFComp_%s_" + region, SIMPF_KIND_LABELS, SIMPF_KIND_COLORS, "total"),
        ("%s, signal part" % COLL_LABELS[coll], "SigComp_" + coll + "_%s_" + region, OFFSET_TYPE_LABELS, OFFSET_COLORS, "total"),
    ]
    tops = []
    for ax, (name, fmt, items, colors, tot) in zip(axes, panels):
        top = _stack(ax, reader, fmt, items, colors, tot)
        if top is not None:
            tops.append(float(np.nanmax(top)))
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 20, 50, 100, 200])
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel(r"$p_T^{GEN}$ [GeV]")
        ax.axhline(1.0, color="gray", linestyle=":", linewidth=1)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], labels[::-1], fontsize="x-small", loc="upper left", frameon=False, title=name, title_fontsize="small")
    axes[0].set_ylabel(r"fraction of $p_T^{GEN}$")
    axes[0].set_ylim(0, 2.1 * max(tops + [1.0]))
    axes[2].text(0.97, 0.96, title, transform=axes[2].transAxes, ha="right", va="top", fontsize="small")
    handles, labels = axes[2].get_legend_handles_labels()
    axes[2].legend(handles[::-1], labels[::-1], fontsize="x-small", loc="upper left", bbox_to_anchor=(0.0, 0.93), ncol=2,
                   frameon=False, title=axes[2].get_legend().get_title().get_text(), title_fontsize="small")
    draw_cms_label(axes[0], cms_label="", data=False, com=13.6)
    fig.subplots_adjust(left=0.065, right=0.99, bottom=0.14, top=0.92, wspace=0.08)
    save_figure(fig, output)
    plt.close(fig)


def efficiency_plot(reader, region, levels, output, title):
    colors, markers = _style(levels)
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graphs[label] = _graph(reader, region, "Eff", level)
        except Exception as err:
            print("skip", level, region, err)
    if graphs:
        plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel="matched fraction",
                    logx=True, ylim=(0.0, 2.0), legend_outside=False, legend_fontsize="x-small",
                    legend_loc="upper right", reference_line=1.0, reference_line_color="black",
                    title=title, connect=True, cms_label="", data=False, markers=markers, colors=colors, hollow_markers=True, markersize=5.5)


def distribution_plot(reader, region, ptbin, levels, output, title):
    use_hep_style()
    fig, ax = plt.subplots(figsize=(9, 7))
    drawn = 0
    for level, label in levels.items():
        try:
            hist = reader.get("all/RespDist_%s_%s_%s" % (level, region, ptbin))
        except Exception:
            continue
        if hist.values.sum() <= 0:
            continue
        norm = hist.values / hist.values.sum()
        style = "--" if level.endswith("Sig") else (":" if level.endswith("Corr") else "-")
        # same colour as in the profile plots, dashed for the signal-only steps
        hep.histplot(norm, hist.edges, ax=ax, label=r"%s, $\langle R\rangle$ = %.2f" % (label, np.average(hist.centers, weights=hist.values)),
                     linestyle=style, histtype="step", linewidth=1.8, color=LEVEL_STYLE[level][1])
        drawn += 1
    if not drawn:
        plt.close(fig)
        return
    ax.set_xlabel(r"$p_T / p_T^{GEN}$")
    ax.set_ylabel("fraction of jets")
    ax.set_xlim(0, 2)
    ymax = ax.get_ylim()[1]
    ax.set_ylim(0, 2.3 * ymax)
    ax.axvline(1.0, color="gray", linestyle=":", linewidth=1)
    ax.text(0.04, 0.96, title, transform=ax.transAxes, ha="left", va="top", fontsize="small")
    ax.legend(fontsize="x-small", loc="upper right", bbox_to_anchor=(0.98, 0.90), frameon=False)
    draw_cms_label(ax, cms_label="", data=False, com=13.6)
    apply_figure_margins(fig)
    save_figure(fig, output)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="run_analysis.py output ROOT file")
    parser.add_argument("--output-dir", default="plots")
    parser.add_argument("--regions", nargs="*", default=list(ETA_REGIONS))
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    out = lambda sub, name: _out(args.output_dir, sub, name)
    with RootFileReader(args.input) as reader:
        for region in args.regions:
            title = REGION_TEXT.get(region, region)
            response_plot(reader, region, SIM_LADDER, out("response_vs_pt", "ladder_sim_%s" % region), title,
                          ylim=(0.3, 1.7), legend_loc="upper right", title_loc="lower left")
            response_plot(reader, region, RECO_LADDER, out("response_vs_pt", "ladder_reco_%s" % region), title,
                          ylim=(0.3, 1.7), legend_loc="upper right", title_loc="lower left")
            response_plot(reader, region, RECO, out("response_vs_pt", "reco_%s" % region), title, ylim=(0.5, 2.9))
            response_plot(reader, region, PUPPI, out("response_vs_pt", "puppijec_%s" % region), title, ylim=(0.5, 1.7),
                          legend_loc="upper right", title_loc="lower left")
            response_plot(reader, region, PILEUP_LADDER, out("response_vs_pt", "ladder_pileup_%s" % region), title, ylim=(0.5, 2.9),
                          legend_loc="upper right", title_loc="lower left", require="SimPFPU")
            response_plot(reader, region, PILEUP_PF, out("response_vs_pt", "pileup_pf_%s" % region), title, ylim=(0.5, 2.9),
                          legend_loc="upper right", title_loc="lower left", require="SimPFPU")
            response_plot(reader, region, PILEUP_CHS, out("response_vs_pt", "pileup_chs_%s" % region), title, ylim=(0.5, 2.9),
                          legend_loc="upper right", title_loc="lower left", require="SimPFPUCHS")
            shared_plot(reader, region, SHARED_SIM, out("response_vs_pt", "shared_sim_%s" % region), title)
            shared_plot(reader, region, SHARED_RECO, out("response_vs_pt", "shared_reco_%s" % region), title)
            efficiency_plot(reader, region, SIM_LADDER, out("efficiency", "efficiency_sim_%s" % region), title)
            efficiency_plot(reader, region, RECO_LADDER, out("efficiency", "efficiency_reco_%s" % region), title)
            offset_total_plot(reader, "Offset_%s_%s_" + region, out("offset", "offset_vs_pt_%s" % region), title, r"$p_T^{GEN}$ [GeV]", True)
            for coll in OFFSET_COLLECTIONS:
                composition_plot(reader, region, coll, out("composition", "composition_%s_%s" % (region, coll)), title)
                offset_composition_plot(reader, "Offset_%s_%s_" + region, coll, out("offset", "offset_vs_pt_%s_%s" % (region, coll)), title, r"$p_T^{GEN}$ [GeV]", True)
                pileup_composition_plot(reader, "OffsetPU_%s_%s_" + region, "OffsetRes_%s_%s_" + region, "Offset_%s_%s_" + region, coll,
                                        out("offset", "pileup_vs_pt_%s_%s" % (region, coll)), title, r"$p_T^{GEN}$ [GeV]", True)
            for lo, hi in PT_BINS:
                lab = pt_bin_label(lo, hi)
                for suffix, levels in (("sim", SIM_LADDER), ("reco", RECO_LADDER)):
                    distribution_plot(reader, region, lab, levels, out("response_dist", "%s_%s_%s" % (region, lab, suffix)),
                                      "%s,  $%d < p_T^{GEN} < %d$ GeV" % (title, lo, hi))
        for lo, hi in PT_BINS:
            lab = pt_bin_label(lo, hi)
            ptitle = r"$%d < p_T^{GEN} < %d$ GeV" % (lo, hi)
            offset_total_plot(reader, "OffsetEta_%s_%s_" + lab, out("offset", "offset_vs_eta_%s" % lab), ptitle, r"$|\eta^{GEN}|$", False)
            for coll in OFFSET_COLLECTIONS:
                offset_composition_plot(reader, "OffsetEta_%s_%s_" + lab, coll, out("offset", "offset_vs_eta_%s_%s" % (lab, coll)), ptitle, r"$|\eta^{GEN}|$", False)
                pileup_composition_plot(reader, "OffsetPUEta_%s_%s_" + lab, "OffsetResEta_%s_%s_" + lab, "OffsetEta_%s_%s_" + lab, coll,
                                        out("offset", "pileup_vs_eta_%s_%s" % (lab, coll)), ptitle, r"$|\eta^{GEN}|$", False)
    print("plots in", args.output_dir)


if __name__ == "__main__":
    main()
