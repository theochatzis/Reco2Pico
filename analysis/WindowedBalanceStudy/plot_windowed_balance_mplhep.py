#!/usr/bin/env python3

"""
mplhep-only Windowed Balance plotting.

ROOT/PyROOT is used only for reading the histogram ROOT files.

Outputs:
  * combined jet-eta comparison
  * fraction composition plots, one per method and eta bin
  * DB nominal vs windowed
  * MPF nominal vs windowed

The MC ROOT file should already contain the event-level NPV reweighting.
"""

import argparse
from collections import OrderedDict
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import warnings

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "SkimRDFAnalysisBase"
sys.path.insert(
    0,
    str(BASE),
)

# Importing plotting first configures local matplotlib cache + Agg explicitly.
from plotting import (  # noqa: E402
    Hist1D,
    Hist2D,
    RootFileReader,
    plot_fraction_composition_data_mc,
    plot_hist1d_methods_data_mc,
)

from plotting.runtime import configure_matplotlib_runtime  # noqa: E402

configure_matplotlib_runtime()

import matplotlib.pyplot as plt  # noqa: E402
import mplhep as hep  # noqa: E402
import numpy as np  # noqa: E402

warnings.filterwarnings(
    "ignore",
    message="The value of the smallest subnormal.*",
    category=UserWarning,
)


ETA_REGIONS = OrderedDict([
    ("eta0to1p3", r"$0.0 \leq |\eta^{jet}| < 1.3$"),
    ("eta1p3to1p5", r"$1.3 \leq |\eta^{jet}| < 1.5$"),
    ("eta1p5to2p5", r"$1.5 \leq |\eta^{jet}| < 2.5$"),
    ("eta2p5to2p7", r"$2.5 \leq |\eta^{jet}| < 2.7$"),
    ("eta2p7to3p0", r"$2.7 \leq |\eta^{jet}| < 3.0$"),
    ("eta3p0to5p0", r"$3.0 \leq |\eta^{jet}| < 5.0$"),
])

FRACTIONS = OrderedDict([
    ("chHEF", "Charged hadron"),
    ("neHEF", "Neutral hadron"),
    ("chEmEF", "Charged EM"),
    ("neEmEF", "Neutral EM"),
    ("muEF", "Muon"),
])

METHODS = OrderedDict([
    ("parallel", "Parallel"),
    ("transverse", "Transverse"),
    ("windowed", "Windowed"),
])

RESPONSE_DISTRIBUTION_METHODS = OrderedDict([
    ("nominal", "Nominal"),
    ("parallel", "Parallel"),
    ("transverse", "Transverse"),
    ("windowed", "Windowed"),
])


def parse_formats(raw):
    formats = []

    for item in raw.split(","):
        item = item.strip().lower().lstrip(".")

        if item and item not in formats:
            formats.append(item)

    if not formats:
        raise ValueError(
            "No output formats requested."
        )

    return formats


def outputs(base, formats):
    base = Path(base)

    return [
        base.with_suffix(
            "." + fmt
        )
        for fmt in formats
    ]


def get_hist(
    reader,
    region,
    name,
):
    path = "{}/{}".format(
        region,
        name,
    )

    obj = reader.get(
        path
    )

    if not isinstance(
        obj,
        Hist1D,
    ):
        raise TypeError(
            "{} is not TH1/TProfile-like; got {}"
            .format(
                path,
                type(obj).__name__,
            )
        )

    return obj


def get_hist2d(
    reader,
    region,
    name,
):
    path = "{}/{}".format(
        region,
        name,
    )

    obj = reader.get(
        path
    )

    if not isinstance(
        obj,
        Hist2D,
    ):
        raise TypeError(
            "{} is not TH2-like; got {}"
            .format(
                path,
                type(obj).__name__,
            )
        )

    return obj


def project_y_bin(
    hist2d,
    xbin,
    name,
):
    """
    Project one TH2 x bin onto its y axis.

    RootFileReader stores Hist2D values with shape:
        (n_y_bins, n_x_bins)
    """
    errors = None

    if hist2d.errors is not None:
        errors = (
            hist2d.errors[
                :,
                xbin,
            ]
            .copy()
        )

    return Hist1D(
        values=(
            hist2d.values[
                :,
                xbin,
            ]
            .copy()
        ),
        edges=hist2d.yedges.copy(),
        errors=errors,
        name=name,
        title=hist2d.title,
        xlabel=hist2d.ylabel,
        ylabel="Weighted jets",
    )


def maybe_stage_local(
    path,
    enabled,
    tempdir,
    label,
):
    path = os.path.abspath(
        os.path.expanduser(
            path
        )
    )

    if (
        not enabled
        or not path.startswith(
            "/eos/"
        )
    ):
        return path

    destination = os.path.join(
        tempdir,
        "{}_{}".format(
            label,
            os.path.basename(
                path
            ),
        ),
    )

    print(
        "Staging {} to local disk..."
        .format(label)
    )

    start = time.time()

    shutil.copy2(
        path,
        destination,
    )

    print(
        "  staged in {:.1f} s"
        .format(
            time.time()
            - start
        )
    )

    return destination


def fraction_components(
    reader,
    args,
    method,
    eta_key,
):
    result = OrderedDict()

    for fraction in FRACTIONS:
        result[fraction] = get_hist(
            reader,
            args.region,
            "Jet_{}_{}_{}_vs_Zpt".format(
                fraction,
                method,
                eta_key,
            ),
        )

    return result


def make_fraction_plots(
    args,
    output_dir,
    data_reader,
    mc_reader,
    formats,
):
    fraction_dir = (
        output_dir
        / "fractions"
    )

    fraction_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for method, method_label in METHODS.items():
        for eta_key, eta_label in ETA_REGIONS.items():
            start = time.time()

            print(
                "  fractions {} {}"
                .format(
                    method,
                    eta_key,
                ),
                end="",
                flush=True,
            )

            data_components = (
                fraction_components(
                    data_reader,
                    args,
                    method,
                    eta_key,
                )
            )

            mc_components = (
                fraction_components(
                    mc_reader,
                    args,
                    method,
                    eta_key,
                )
            )

            fixed_ratio = None

            if not args.fractions_ratio_auto:
                fixed_ratio = (
                    args.fractions_ratio_min,
                    args.fractions_ratio_max,
                )

            plot_fraction_composition_data_mc(
                data_components,
                mc_components,
                outputs(
                    fraction_dir
                    / "fractions_{}_{}".format(
                        method,
                        eta_key,
                    ),
                    formats,
                ),
                labels=FRACTIONS,
                xlabel=r"$p_T^Z$ [GeV]",
                ylabel="Energy fraction",
                ratio_label="Data / MC",
                cms_label=args.cms_label,
                lumi=args.lumi,
                com=args.com,
                method_label=method_label,
                eta_label=eta_label,
                xlim=(
                    args.zpt_min,
                    args.zpt_max,
                ),
                logx=args.fractions_logx,
                ratio_ylim=fixed_ratio,
                auto_ratio_y=(
                    args.fractions_ratio_auto
                ),
                ratio_padding=(
                    args.fractions_ratio_padding
                ),
                mc_ratio_uncertainty_band=(
                    args.mc_ratio_uncertainty_band
                ),
            )

            print(
                " [{:.1f} s]"
                .format(
                    time.time()
                    - start
                )
            )


def make_method_distribution_plot(
    args,
    output_dir,
    data_reader,
    mc_reader,
    formats,
    *,
    observable,
    histogram_names,
    xlabel,
    ylabel,
    xlim=None,
    logx=False,
    side_text=None,
):
    """
    Plot Parallel / Transverse / Windowed as ordinary 1D distributions.

    The visual convention is intentionally the same as the jet-eta plot:
      * Data = markers
      * MC   = histogram steps
      * lower panel = Data / MC
      * optional MC uncertainty band around one

    For the windowed histogram the subtraction is already encoded through
    weight_windowed in the YAML.
    """
    data_methods = OrderedDict()
    mc_methods = OrderedDict()

    for method in METHODS:
        histogram_name = histogram_names[method]

        data_methods[method] = get_hist(
            data_reader,
            args.region,
            histogram_name,
        )

        mc_methods[method] = get_hist(
            mc_reader,
            args.region,
            histogram_name,
        )

    plot_hist1d_methods_data_mc(
        data_methods,
        mc_methods,
        outputs(
            output_dir
            / "{}_parallel_transverse_windowed".format(
                observable
            ),
            formats,
        ),
        labels=METHODS,
        xlabel=xlabel,
        ylabel=ylabel,
        ratio_label="Data / MC",
        normalize_mc_to_data=(
            args.distribution_normalize_mc
        ),
        xlim=xlim,
        auto_y=True,
        ratio_ylim=(
            args.distribution_ratio_min,
            args.distribution_ratio_max,
        ),
        auto_ratio_y=False,
        mc_ratio_uncertainty_band=(
            args.mc_ratio_uncertainty_band
        ),
        logx=logx,
        legend_outside=True,
        legend_fontsize="x-small",
        ratio_legend=False,
        side_text=side_text,
        cms_label=args.cms_label,
        lumi=args.lumi,
        com=args.com,
        title=None,
    )


def make_method_distributions(
    args,
    output_dir,
    data_reader,
    mc_reader,
    formats,
):
    """
    Standard Data/MC distributions for the three sampling methods:
      Jet eta, Z pT, DB and MPF.

    All ordinary method distributions are handled through the same generic
    make_method_distribution_plot() path.
    """
    distribution_dir = (
        output_dir
        / "distributions"
    )
    distribution_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pt_tag = (
        args.pt_tag
        if args.pt_tag
        else (
            r"${:.0f} < p_T^Z < {:.0f}\,\mathrm{{GeV}}$"
            .format(
                args.zpt_min,
                args.zpt_max,
            )
        )
    )

    # Jet eta.
    make_method_distribution_plot(
        args,
        distribution_dir,
        data_reader,
        mc_reader,
        formats,
        observable="Jet_eta",
        histogram_names={
            "parallel": "Jet_eta_parallel",
            "transverse": "Jet_eta_transverse",
            "windowed": "Jet_eta_windowed",
        },
        xlabel=r"$\eta^{jet}$",
        ylabel="Jets",
        xlim=None,
        logx=False,
        side_text=pt_tag,
    )

    # Z pT: no pT-selection tag because pT itself is the plotted observable.
    make_method_distribution_plot(
        args,
        distribution_dir,
        data_reader,
        mc_reader,
        formats,
        observable="Zpt",
        histogram_names={
            "parallel": "Z_pt_parallel_distribution",
            "transverse": "Z_pt_transverse_distribution",
            "windowed": "Z_pt_windowed_distribution",
        },
        xlabel=r"$p_T^Z$ [GeV]",
        ylabel="Weighted jets",
        xlim=(
            args.zpt_min,
            args.zpt_max,
        ),
        logx=args.distribution_zpt_logx,
        side_text=None,
    )

    # Raw DB distribution.
    make_method_distribution_plot(
        args,
        distribution_dir,
        data_reader,
        mc_reader,
        formats,
        observable="DB",
        histogram_names={
            "parallel": "DB_parallel",
            "transverse": "DB_transverse",
            "windowed": "DB_windowed",
        },
        xlabel=r"$p_T^{jet}/p_T^Z$",
        ylabel="Weighted jets",
        xlim=(
            args.db_distribution_min,
            args.db_distribution_max,
        ),
        logx=False,
        side_text=pt_tag,
    )

    # Raw MPF distribution.
    make_method_distribution_plot(
        args,
        distribution_dir,
        data_reader,
        mc_reader,
        formats,
        observable="MPF",
        histogram_names={
            "parallel": "MPF_parallel",
            "transverse": "MPF_transverse",
            "windowed": "MPF_windowed",
        },
        xlabel="MPF response",
        ylabel="Weighted jets",
        xlim=(
            args.mpf_distribution_min,
            args.mpf_distribution_max,
        ),
        logx=False,
        side_text=pt_tag,
    )




def parse_method_list(raw):
    methods = []

    for item in raw.split(","):
        item = item.strip()

        if not item:
            continue

        if item not in RESPONSE_DISTRIBUTION_METHODS:
            raise ValueError(
                "Unknown response-distribution method '{}'. "
                "Allowed: {}"
                .format(
                    item,
                    ", ".join(
                        RESPONSE_DISTRIBUTION_METHODS.keys()
                    ),
                )
            )

        if item not in methods:
            methods.append(
                item
            )

    if not methods:
        raise ValueError(
            "No pT-slice response methods selected."
        )

    return methods


def make_response_distributions_by_zpt(
    args,
    output_dir,
    data_reader,
    mc_reader,
    formats,
):
    """
    Draw the complete DB and MPF response distributions separately for every
    Z-pT bin.

    The ROOT output contains one TH2D per method:
        x = pT(Z)
        y = DB or MPF

    This function projects one x bin at a time and feeds the resulting Hist1D
    objects into the same generic Data/MC plotting code used everywhere else.
    """
    selected_methods = parse_method_list(
        args.ptz_slice_methods
    )

    slice_dir = (
        output_dir
        / "response_distributions_by_zpt"
    )

    configurations = OrderedDict([
        (
            "DB",
            {
                "xlabel": r"$p_T^{jet}/p_T^Z$",
                "xlim": (
                    args.db_distribution_min,
                    args.db_distribution_max,
                ),
            },
        ),
        (
            "MPF",
            {
                "xlabel": "MPF response",
                "xlim": (
                    args.mpf_distribution_min,
                    args.mpf_distribution_max,
                ),
            },
        ),
    ])

    for observable, config in configurations.items():

        observable_dir = (
            slice_dir
            / observable
        )

        observable_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        data_maps = OrderedDict()
        mc_maps = OrderedDict()

        for method in selected_methods:

            histogram_name = (
                "{}_{}_vs_Zpt_2D"
                .format(
                    observable,
                    method,
                )
            )

            data_maps[method] = get_hist2d(
                data_reader,
                args.region,
                histogram_name,
            )

            mc_maps[method] = get_hist2d(
                mc_reader,
                args.region,
                histogram_name,
            )

        reference = data_maps[
            selected_methods[0]
        ]

        pt_edges = reference.xedges

        # Check that every method and Data/MC file uses identical pT binning.
        for method in selected_methods:
            if not np.allclose(
                data_maps[method].xedges,
                pt_edges,
            ):
                raise ValueError(
                    "Data pT binning differs for {}".format(
                        method
                    )
                )

            if not np.allclose(
                mc_maps[method].xedges,
                pt_edges,
            ):
                raise ValueError(
                    "MC pT binning differs for {}".format(
                        method
                    )
                )

        for xbin in range(
            len(pt_edges) - 1
        ):
            pt_min = float(
                pt_edges[xbin]
            )
            pt_max = float(
                pt_edges[xbin + 1]
            )

            # Restrict the generated plot set if requested.
            if (
                args.ptz_slice_min is not None
                and pt_max
                <= args.ptz_slice_min
            ):
                continue

            if (
                args.ptz_slice_max is not None
                and pt_min
                >= args.ptz_slice_max
            ):
                continue

            data_methods = OrderedDict()
            mc_methods = OrderedDict()

            for method in selected_methods:

                data_methods[method] = project_y_bin(
                    data_maps[method],
                    xbin,
                    "{}_{}_data_ptbin{}".format(
                        observable,
                        method,
                        xbin,
                    ),
                )

                mc_methods[method] = project_y_bin(
                    mc_maps[method],
                    xbin,
                    "{}_{}_mc_ptbin{}".format(
                        observable,
                        method,
                        xbin,
                    ),
                )

            labels = OrderedDict([
                (
                    method,
                    RESPONSE_DISTRIBUTION_METHODS[
                        method
                    ],
                )
                for method in selected_methods
            ])

            pt_label = (
                r"${:g} < p_T^Z < {:g}\,\mathrm{{GeV}}$"
                .format(
                    pt_min,
                    pt_max,
                )
            )

            file_tag = (
                "ptZ_{}to{}"
                .format(
                    "{:g}".format(
                        pt_min
                    ).replace(
                        ".",
                        "p",
                    ),
                    "{:g}".format(
                        pt_max
                    ).replace(
                        ".",
                        "p",
                    ),
                )
            )

            plot_hist1d_methods_data_mc(
                data_methods,
                mc_methods,
                outputs(
                    observable_dir
                    / "{}_{}".format(
                        observable,
                        file_tag,
                    ),
                    formats,
                ),
                labels=labels,
                xlabel=config[
                    "xlabel"
                ],
                ylabel="Weighted jets",
                ratio_label="Data / MC",
                normalize_mc_to_data=(
                    args.ptz_slice_normalize_mc
                ),
                xlim=config[
                    "xlim"
                ],
                auto_y=True,
                ratio_ylim=(
                    args.distribution_ratio_min,
                    args.distribution_ratio_max,
                ),
                auto_ratio_y=False,
                mc_ratio_uncertainty_band=(
                    args.mc_ratio_uncertainty_band
                ),
                legend_outside=True,
                legend_fontsize="x-small",
                ratio_legend=False,
                side_text=pt_label,
                cms_label=args.cms_label,
                lumi=args.lumi,
                com=args.com,
                title=None,
            )



def make_response_plot(
    args,
    output_dir,
    data_reader,
    mc_reader,
    formats,
    observable,
):
    data_methods = OrderedDict([
        (
            "nominal",
            get_hist(
                data_reader,
                args.region,
                "{}_nominal_vs_Zpt".format(
                    observable
                ),
            ),
        ),
        (
            "windowed",
            get_hist(
                data_reader,
                args.region,
                "{}_windowed_vs_Zpt".format(
                    observable
                ),
            ),
        ),
    ])

    mc_methods = OrderedDict([
        (
            "nominal",
            get_hist(
                mc_reader,
                args.region,
                "{}_nominal_vs_Zpt".format(
                    observable
                ),
            ),
        ),
        (
            "windowed",
            get_hist(
                mc_reader,
                args.region,
                "{}_windowed_vs_Zpt".format(
                    observable
                ),
            ),
        ),
    ])

    labels = OrderedDict([
        ("nominal", "Nominal"),
        ("windowed", "Windowed"),
    ])

    fixed_y = None

    if (
        args.response_y_min
        is not None
        and
        args.response_y_max
        is not None
    ):
        fixed_y = (
            args.response_y_min,
            args.response_y_max,
        )

    fixed_ratio = None

    if (
        args.response_ratio_min
        is not None
        and
        args.response_ratio_max
        is not None
    ):
        fixed_ratio = (
            args.response_ratio_min,
            args.response_ratio_max,
        )

    if observable == "DB":
        ylabel = "Direct balance"
        title = (
            "Direct balance: "
            "nominal vs windowed"
        )
    else:
        ylabel = "MPF response"
        title = (
            "MPF: nominal vs windowed"
        )

    plot_hist1d_methods_data_mc(
        data_methods,
        mc_methods,
        outputs(
            output_dir
            / "{}_nominal_vs_windowed".format(
                observable
            ),
            formats,
        ),
        labels=labels,
        xlabel=r"$p_T^Z$ [GeV]",
        ylabel=ylabel,
        ratio_label="Data / MC",
        xlim=(
            args.zpt_min,
            args.zpt_max,
        ),
        ylim=fixed_y,
        auto_y=(
            fixed_y is None
        ),
        y_padding=(
            args.response_y_padding
        ),
        ratio_ylim=fixed_ratio,
        auto_ratio_y=(
            fixed_ratio is None
        ),
        ratio_padding=(
            args.response_ratio_padding
        ),
        mc_ratio_uncertainty_band=(
            args.mc_ratio_uncertainty_band
        ),
        legend_outside=True,
        ratio_legend=False,
        side_text=(
            args.response_tag
            if args.response_tag
            else None
        ),
        cms_label=args.cms_label,
        lumi=args.lumi,
        com=args.com,
        title=title,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        required=True,
    )

    parser.add_argument(
        "--mc",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        default="plots_mplhep",
    )

    parser.add_argument(
        "--region",
        default="zjet",
    )

    parser.add_argument(
        "--formats",
        default="png",
        help=(
            "Comma-separated output formats. "
            "Use pdf,png for final plots."
        ),
    )

    parser.add_argument(
        "--only",
        choices=(
            "all",
            "fractions",
            "distributions",
            "response",
            "ptz-slices",
        ),
        default="all",
    )

    parser.add_argument(
        "--stage-local",
        action="store_true",
    )

    parser.add_argument(
        "--cms-label",
        default="Preliminary",
    )

    parser.add_argument(
        "--lumi",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--com",
        type=float,
        default=13.6,
    )

    parser.add_argument(
        "--zpt-min",
        type=float,
        default=30.0,
    )

    parser.add_argument(
        "--zpt-max",
        type=float,
        default=500.0,
    )

    parser.add_argument(
        "--pt-tag",
        default="",
        help=(
            "Optional custom pT-selection tag for eta/DB/MPF distributions. "
            "If empty, a tag is generated from --zpt-min/max."
        ),
    )

    parser.add_argument(
        "--response-tag",
        default="",
        help=(
            "Optional extra tag shown in the side column of DB/MPF plots."
        ),
    )

    parser.add_argument(
        "--fractions-logx",
        action="store_true",
        default=True,
    )

    parser.add_argument(
        "--fractions-linear-x",
        dest="fractions_logx",
        action="store_false",
    )

    parser.add_argument(
        "--fractions-ratio-min",
        type=float,
        default=0.8,
        help=(
            "Fixed lower limit of the fraction Data/MC panel. "
            "Default: automatic."
        ),
    )

    parser.add_argument(
        "--fractions-ratio-max",
        type=float,
        default=1.2,
        help=(
            "Fixed upper limit of the fraction Data/MC panel. "
            "Default: automatic."
        ),
    )

    parser.add_argument(
        "--fractions-ratio-padding",
        type=float,
        default=0.12,
    )

    parser.add_argument(
        "--fractions-ratio-auto",
        action="store_true",
        help=(
            "Automatically determine the fraction Data/MC y range. "
            "Default is the fixed --fractions-ratio-min/max range."
        ),
    )

    parser.add_argument(
        "--mc-ratio-uncertainty-band",
        dest="mc_ratio_uncertainty_band",
        action="store_true",
        default=True,
        help=(
            "Show MC statistical uncertainty as a shaded band "
            "around 1 in Data/MC panels (default)."
        ),
    )

    parser.add_argument(
        "--no-mc-ratio-uncertainty-band",
        dest="mc_ratio_uncertainty_band",
        action="store_false",
        help="Disable the MC uncertainty band in Data/MC panels.",
    )

    parser.add_argument(
        "--distribution-ratio-min",
        type=float,
        default=0.5,
        help="Lower Data/MC limit for eta/Zpt/DB/MPF distributions.",
    )

    parser.add_argument(
        "--distribution-ratio-max",
        type=float,
        default=1.5,
        help="Upper Data/MC limit for eta/Zpt/DB/MPF distributions.",
    )

    parser.add_argument(
        "--distribution-normalize-mc",
        dest="distribution_normalize_mc",
        action="store_true",
        default=True,
        help=(
            "Normalize each MC method distribution to the corresponding "
            "Data integral before plotting (default)."
        ),
    )

    parser.add_argument(
        "--no-distribution-normalize-mc",
        dest="distribution_normalize_mc",
        action="store_false",
        help=(
            "Keep the absolute weighted MC normalization. Useful when "
            "inspecting the relative parallel/transverse/windowed yields."
        ),
    )

    parser.add_argument(
        "--distribution-zpt-logx",
        action="store_true",
        default=True,
        help="Use logarithmic pT axis for the Z-pT method distribution.",
    )

    parser.add_argument(
        "--distribution-zpt-linear-x",
        dest="distribution_zpt_logx",
        action="store_false",
        help="Use a linear pT axis for the Z-pT method distribution.",
    )

    parser.add_argument(
        "--db-distribution-min",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--db-distribution-max",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--mpf-distribution-min",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--mpf-distribution-max",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--ptz-slice-methods",
        default="parallel,transverse,windowed",
        help=(
            "Comma-separated methods to draw in every pT(Z) response "
            "distribution. Allowed: nominal,parallel,transverse,windowed."
        ),
    )

    parser.add_argument(
        "--ptz-slice-min",
        type=float,
        default=None,
        help=(
            "Optional minimum pT(Z) edge for response-distribution slices."
        ),
    )

    parser.add_argument(
        "--ptz-slice-max",
        type=float,
        default=None,
        help=(
            "Optional maximum pT(Z) edge for response-distribution slices."
        ),
    )

    parser.add_argument(
        "--ptz-slice-normalize-mc",
        dest="ptz_slice_normalize_mc",
        action="store_true",
        default=True,
        help=(
            "Normalize each MC response distribution to the corresponding "
            "Data integral in each pT(Z) bin (default)."
        ),
    )

    parser.add_argument(
        "--no-ptz-slice-normalize-mc",
        dest="ptz_slice_normalize_mc",
        action="store_false",
        help=(
            "Keep absolute weighted MC normalization in the pT(Z)-slice "
            "response distributions."
        ),
    )

    parser.add_argument(
        "--response-y-min",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--response-y-max",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--response-y-padding",
        type=float,
        default=0.12,
    )

    parser.add_argument(
        "--response-ratio-min",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--response-ratio-max",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--response-ratio-padding",
        type=float,
        default=0.12,
    )

    args = parser.parse_args()

    if (
        (args.response_y_min is None)
        != (args.response_y_max is None)
    ):
        parser.error(
            "--response-y-min and --response-y-max "
            "must be supplied together."
        )

    if (
        (args.response_ratio_min is None)
        != (args.response_ratio_max is None)
    ):
        parser.error(
            "--response-ratio-min and --response-ratio-max "
            "must be supplied together."
        )

    formats = parse_formats(
        args.formats
    )

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_start = time.time()

    print(
        "Matplotlib cache: {}"
        .format(
            os.environ.get(
                "MPLCONFIGDIR"
            )
        )
    )

    with tempfile.TemporaryDirectory(
        prefix="windowed_balance_mplhep_"
    ) as tempdir:

        data_path = maybe_stage_local(
            args.data,
            args.stage_local,
            tempdir,
            "data",
        )

        mc_path = maybe_stage_local(
            args.mc,
            args.stage_local,
            tempdir,
            "mc",
        )

        print(
            "Opening ROOT files..."
        )

        io_start = time.time()

        with RootFileReader(
            data_path
        ) as data_reader, RootFileReader(
            mc_path
        ) as mc_reader:

            print(
                "  opened in {:.1f} s"
                .format(
                    time.time()
                    - io_start
                )
            )

            if args.only in (
                "all",
                "fractions",
            ):
                start = time.time()

                print(
                    "Making fraction composition plots..."
                )

                make_fraction_plots(
                    args,
                    output_dir,
                    data_reader,
                    mc_reader,
                    formats,
                )

                print(
                    "  fractions total: {:.1f} s"
                    .format(
                        time.time()
                        - start
                    )
                )

            if args.only in (
                "all",
                "distributions",
            ):
                start = time.time()

                print(
                    "Making eta/Zpt/DB/MPF method distributions..."
                )

                make_method_distributions(
                    args,
                    output_dir,
                    data_reader,
                    mc_reader,
                    formats,
                )

                print(
                    "  distributions: {:.1f} s"
                    .format(
                        time.time()
                        - start
                    )
                )

            if args.only == "ptz-slices":
                start = time.time()

                print(
                    "Making DB/MPF distributions in every pT(Z) bin..."
                )

                make_response_distributions_by_zpt(
                    args,
                    output_dir,
                    data_reader,
                    mc_reader,
                    formats,
                )

                print(
                    "  pT(Z) slices: {:.1f} s"
                    .format(
                        time.time()
                        - start
                    )
                )

            if args.only in (
                "all",
                "response",
            ):
                start = time.time()

                print(
                    "Making DB/MPF plots..."
                )

                make_response_plot(
                    args,
                    output_dir,
                    data_reader,
                    mc_reader,
                    formats,
                    "DB",
                )

                make_response_plot(
                    args,
                    output_dir,
                    data_reader,
                    mc_reader,
                    formats,
                    "MPF",
                )

                print(
                    "  response: {:.1f} s"
                    .format(
                        time.time()
                        - start
                    )
                )

            print(
                "Cached ROOT objects: "
                "data={}, mc={}"
                .format(
                    len(
                        data_reader._cache
                    ),
                    len(
                        mc_reader._cache
                    ),
                )
            )

    print(
        "Total plotting time: {:.1f} s"
        .format(
            time.time()
            - total_start
        )
    )

    print(
        "Plots written under: {}"
        .format(
            output_dir
        )
    )


if __name__ == "__main__":
    main()
