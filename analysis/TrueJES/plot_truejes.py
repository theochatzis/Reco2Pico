#!/usr/bin/env python3
"""
TrueJES plots from the run_analysis.py output, every figure as .pdf and .png:

  response_vs_pt/ladder_<region>      <pT/pT_GEN> vs pT_GEN, one curve per ladder step
  response_vs_pt/reco_<region>        the reconstructed steps, raw and signal-only
  response_vs_pt/shared_<region>      <E_shared/E_GEN> vs pT_GEN: only the energy descending from the gen jet
  response_vs_pt/puppijec_<region>    raw and JEC-corrected Puppi jets, full and signal part, with the ideal PF
  efficiency/efficiency_<region>      matched fraction vs pT_GEN per step
  response_dist/<region>_<ptbin>      response distributions per step in one gen-pt bin

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

from truejes_rdf_definition import ETA_REGIONS, LEVELS, PT_BINS, SHARED_LEVELS, pt_bin_label  # noqa: E402
from plotting import RootFileReader, hist_to_graph, plot_graphs  # noqa: E402
from plotting.plotters import use_hep_style, save_figure, draw_cms_label  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mplhep as hep  # noqa: E402

LADDER = OrderedDict([
    ("Sim", "SimJet (Geant4 particles)"),
    ("SimCalo", "SimCaloJet (calo deposits)"),
    ("SimPF", "SimPFJet (ideal PF)"),
    ("PFSig", "PF jet, signal part"),
    ("CHSSig", "CHS jet, signal part"),
    ("PuppiSig", "Puppi jet, signal part"),
])
RECO = OrderedDict([
    ("PF", "PF jet (raw, with pile-up)"),
    ("PFSig", "PF jet, signal part"),
    ("CHS", "CHS jet (raw)"),
    ("CHSSig", "CHS jet, signal part"),
    ("Puppi", "Puppi jet (raw)"),
    ("PuppiSig", "Puppi jet, signal part"),
])
SHARED = OrderedDict([
    ("Sim", "SimJet (Geant4 particles)"),
    ("SimCalo", "SimCaloJet (calo deposits)"),
    ("SimPF", "SimPFJet (ideal PF)"),
    ("PF", "PF jet"),
    ("CHS", "CHS jet"),
    ("Puppi", "Puppi jet"),
])
PUPPI = OrderedDict([
    ("Puppi", "Puppi jet (raw)"),
    ("PuppiCorr", "Puppi jet, JEC L1L2L3"),
    ("PuppiSig", "Puppi jet, signal part (raw)"),
    ("PuppiSigCorr", "Puppi jet, signal part, JEC L2L3"),
    ("SimPF", "SimPFJet (ideal PF)"),
])
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


def response_plot(reader, region, levels, output, title, ylim=(0.3, 1.5)):
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graphs[label] = _graph(reader, region, "Resp", level)
        except Exception as err:  # missing histogram
            print("skip", level, region, err)
    if not graphs:
        return
    plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel=r"$\langle p_T / p_T^{GEN} \rangle$",
                logx=True, reference_line=1.0, ylim=ylim, legend_outside=False, legend_fontsize="x-small",
                title=title, connect=True, cms_label="", data=False)


def shared_plot(reader, region, levels, output, title):
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graphs[label] = _graph(reader, region, "RespShared", level)
        except Exception as err:
            print("skip", level, region, err)
    if graphs:
        plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel=r"$\langle E_{shared} / E^{GEN} \rangle$",
                    logx=True, reference_line=1.0, ylim=(0.3, 1.5), legend_outside=False, legend_fontsize="x-small",
                    title=title, connect=True, cms_label="", data=False)


def efficiency_plot(reader, region, levels, output, title):
    graphs = OrderedDict()
    for level, label in levels.items():
        try:
            graphs[label] = _graph(reader, region, "Eff", level)
        except Exception as err:
            print("skip", level, region, err)
    if graphs:
        plot_graphs(graphs, output, xlabel=r"$p_T^{GEN}$ [GeV]", ylabel="matched fraction",
                    logx=True, ylim=(0.0, 1.75), legend_outside=False, legend_fontsize="x-small",
                    title=title, connect=True, cms_label="", data=False)


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
        style = "--" if level.endswith("Sig") else "-"
        # same colour cycle as the profile plots (plot_graphs), dashed for the signal-only steps
        hep.histplot(norm, hist.edges, ax=ax, label=r"%s, $\langle R\rangle$ = %.2f" % (label, np.average(hist.centers, weights=hist.values)),
                     linestyle=style, histtype="step", linewidth=1.8)
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
            response_plot(reader, region, LADDER, out("response_vs_pt", "ladder_%s" % region), title)
            response_plot(reader, region, RECO, out("response_vs_pt", "reco_%s" % region), title, ylim=(0.5, 2.5))
            response_plot(reader, region, PUPPI, out("response_vs_pt", "puppijec_%s" % region), title, ylim=(0.5, 1.7))
            shared_plot(reader, region, SHARED, out("response_vs_pt", "shared_%s" % region), title)
            efficiency_plot(reader, region, LADDER, out("efficiency", "efficiency_%s" % region), title)
            for lo, hi in PT_BINS:
                lab = pt_bin_label(lo, hi)
                distribution_plot(reader, region, lab, LADDER, out("response_dist", "%s_%s" % (region, lab)),
                                  "%s,  $%d < p_T^{GEN} < %d$ GeV" % (title, lo, hi))
    print("plots in", args.output_dir)


if __name__ == "__main__":
    main()
