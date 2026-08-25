#!/usr/bin/env python3

"""
Plot the compact Z+jet profile maps.

Only Nominal and Windowed are drawn.

Views
-----
distributions
    Z pT
    jet eta in pT(Z) = [0,20], [20,50], [>50] GeV
    raw DB in the same pT categories
    raw MPF in the same pT categories

responses-vs-pt
    <DB>, <MPF> vs pT(Z)
    for the six coarse |eta| regions
    pT(Z) is logarithmic

responses-vs-eta
    <DB>, <MPF> vs the fine signed eta binning
    for pT(Z) = [0,20], [20,50], [>50] GeV

fractions
    composition vs pT(Z) in the six coarse |eta| regions
    pT(Z) is logarithmic
"""

import argparse
from collections import OrderedDict
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "SkimRDFAnalysisBase"

sys.path.insert(
    0,
    str(BASE),
)

from plotting import (  # noqa: E402
    Hist1D,
    Hist2D,
    RootFileReader,
    plot_fraction_composition_data_mc,
    plot_hist1d_methods_data_mc,
)


PROFILE_METHODS = OrderedDict([
    ("nominal", "Nominal"),
    ("windowed", "Windowed"),
])

FRACTION_METHODS = OrderedDict([
    ("nominal", "Nominal"),
    ("parallel", "Parallel"),
    ("transverse", "Transverse"),
    ("windowed", "Windowed"),
])

DISTRIBUTION_METHODS = OrderedDict([
    ("parallel", "Parallel"),
    ("transverse", "Transverse"),
    ("windowed", "Windowed"),
])

FRACTIONS = OrderedDict([
    ("chHEF", "Charged hadron"),
    ("neHEF", "Neutral hadron"),
    ("chEmEF", "Charged EM"),
    ("neEmEF", "Neutral EM"),
    ("muEF", "Muon"),
])

COARSE_ABS_ETA_REGIONS = OrderedDict([
    ("eta0to1p3",   (0.0, 1.3)),
    ("eta1p3to1p5", (1.3, 1.5)),
    ("eta1p5to2p5", (1.5, 2.5)),
    ("eta2p5to2p7", (2.5, 2.7)),
    ("eta2p7to3p0", (2.7, 3.0)),
    ("eta3p0to5p0", (3.0, 5.0)),
])

PT_CATEGORIES = OrderedDict([
    ("ptZ_5to15",  (5.0, 15.0,  r"$5 \leq p_T^Z < 15\,\mathrm{GeV}$")),
    ("ptZ_15to50", (15.0, 30.0, r"$15 \leq p_T^Z < 30\,\mathrm{GeV}$")),
    ("ptZ_30to50", (30.0, 50.0, r"$30 \leq p_T^Z < 50\,\mathrm{GeV}$")),
    ("ptZ_30to200", (30.0, 200.0, r"$30 \leq p_T^Z < 200\,\mathrm{GeV}$")),
    ("ptZ_50to100", (50.0, 100.0, r"$50 \leq p_T^Z < 100\,\mathrm{GeV}$")),
    ("ptZ_100to200", (100.0, 200.0, r"$100 \leq p_T^Z < 200\,\mathrm{GeV}$")),
    ("ptZ_gt200",   (200.0, None,  r"$p_T^Z \geq 200\,\mathrm{GeV}$")),
])


def parse_formats(raw):
    formats = []

    for value in raw.split(","):
        value = (
            value.strip()
            .lower()
            .lstrip(".")
        )

        if (
            value
            and value not in formats
        ):
            formats.append(
                value
            )

    return formats


def outputs(base, formats):
    base = Path(
        base
    )

    return [
        base.with_suffix(
            "." + extension
        )
        for extension in formats
    ]


def get_map(
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
            "{} is not TH2/TProfile2D-like"
            .format(path)
        )

    return obj


def validate_fine_eta_input(
    hist,
    *,
    context="eta plot",
):
    """
    Guard against accidentally plotting ROOT files produced with an older
    coarse-eta YAML.

    The current configuration has ~92 signed eta bins and includes the
    characteristic central HCAL edge at |eta| = 0.087.
    """
    edges = np.asarray(
        hist.yedges,
        dtype=float,
    )

    n_bins = len(edges) - 1

    has_hcal_edge = np.any(
        np.isclose(
            np.abs(edges),
            0.087,
            atol=1e-6,
            rtol=0.0,
        )
    )

    if (
        n_bins < 70
        or not has_hcal_edge
    ):
        raise RuntimeError(
            "{} is using a coarse eta axis ({} bins). "
            "The current study expects the fine HCAL-like eta binning. "
            "Regenerate zjet_histograms.yaml with make_zjet_profile_maps.py "
            "and rerun run_analysis.py to create new ROOT files before "
            "plotting."
            .format(
                context,
                n_bins,
            )
        )


def eta_centers(hist):
    return (
        0.5
        * (
            hist.yedges[:-1]
            + hist.yedges[1:]
        )
    )


def pt_centers(hist):
    return (
        0.5
        * (
            hist.xedges[:-1]
            + hist.xedges[1:]
        )
    )


def pt_bin_mask(
    hist,
    low,
    high,
):
    """
    Select complete profile-map pT bins.

    The central PTZ_EDGES contain exact 20 and 50 GeV boundaries,
    therefore the three broad categories are represented exactly.
    """
    lows = hist.xedges[:-1]
    highs = hist.xedges[1:]

    mask = (
        lows >= low
    )

    if high is not None:
        mask = (
            mask
            & (
                highs <= high
            )
        )

    return mask


def abs_eta_mask(
    hist,
    low,
    high,
):
    centers = eta_centers(
        hist
    )

    return (
        (np.abs(centers) >= low)
        & (np.abs(centers) < high)
    )


def combine_profile_bins(
    profile,
    count_map,
    *,
    eta_mask=None,
    pt_mask=None,
    output_axis,
    name="",
):
    """
    Combine TProfile2D cells using the matching count-map sum of weights.

    Central values are exact:
        mean = sum(sumW_cell * mean_cell) / sum(sumW_cell)

    The combined uncertainty is an approximate propagation of the stored
    per-cell profile errors:
        sigma ~= sqrt(sum((sumW_cell * sigma_cell)^2)) / |sumW|

    This is sufficient for plotting; exact combined TProfile errors would
    require retaining additional ROOT profile internals.
    """
    means = np.asarray(
        profile.values,
        dtype=float,
    )

    weights = np.asarray(
        count_map.values,
        dtype=float,
    )

    errors = (
        None
        if profile.errors is None
        else np.asarray(
            profile.errors,
            dtype=float,
        )
    )

    if output_axis == "pt":
        if eta_mask is None:
            raise ValueError(
                "eta_mask is required for output_axis='pt'."
            )

        selected_means = means[
            eta_mask,
            :
        ]

        selected_weights = weights[
            eta_mask,
            :
        ]

        denominator = np.sum(
            selected_weights,
            axis=0,
        )

        numerator = np.sum(
            selected_weights
            * selected_means,
            axis=0,
        )

        values = np.full_like(
            denominator,
            np.nan,
            dtype=float,
        )

        valid = (
            np.isfinite(denominator)
            & (np.abs(denominator) > 1e-12)
        )

        values[valid] = (
            numerator[valid]
            / denominator[valid]
        )

        combined_errors = None

        if errors is not None:
            selected_errors = errors[
                eta_mask,
                :
            ]

            variance = np.sum(
                (
                    selected_weights
                    * selected_errors
                ) ** 2,
                axis=0,
            )

            combined_errors = np.full_like(
                denominator,
                np.nan,
                dtype=float,
            )

            combined_errors[valid] = (
                np.sqrt(
                    variance[valid]
                )
                / np.abs(
                    denominator[valid]
                )
            )

        return Hist1D(
            values=values,
            edges=profile.xedges.copy(),
            errors=combined_errors,
            name=name,
            xlabel=profile.xlabel,
            ylabel=profile.zlabel,
        )

    if output_axis == "eta":
        if pt_mask is None:
            raise ValueError(
                "pt_mask is required for output_axis='eta'."
            )

        selected_means = means[
            :,
            pt_mask
        ]

        selected_weights = weights[
            :,
            pt_mask
        ]

        denominator = np.sum(
            selected_weights,
            axis=1,
        )

        numerator = np.sum(
            selected_weights
            * selected_means,
            axis=1,
        )

        values = np.full_like(
            denominator,
            np.nan,
            dtype=float,
        )

        valid = (
            np.isfinite(denominator)
            & (np.abs(denominator) > 1e-12)
        )

        values[valid] = (
            numerator[valid]
            / denominator[valid]
        )

        combined_errors = None

        if errors is not None:
            selected_errors = errors[
                :,
                pt_mask
            ]

            variance = np.sum(
                (
                    selected_weights
                    * selected_errors
                ) ** 2,
                axis=1,
            )

            combined_errors = np.full_like(
                denominator,
                np.nan,
                dtype=float,
            )

            combined_errors[valid] = (
                np.sqrt(
                    variance[valid]
                )
                / np.abs(
                    denominator[valid]
                )
            )

        return Hist1D(
            values=values,
            edges=profile.yedges.copy(),
            errors=combined_errors,
            name=name,
            xlabel=profile.ylabel,
            ylabel=profile.zlabel,
        )

    raise ValueError(
        "Unknown output axis: {}".format(
            output_axis
        )
    )


def project_count_vs_pt(
    count_map,
    name="",
):
    values = np.sum(
        count_map.values,
        axis=0,
    )

    errors = None

    if count_map.errors is not None:
        errors = np.sqrt(
            np.sum(
                count_map.errors ** 2,
                axis=0,
            )
        )

    return Hist1D(
        values=values,
        edges=count_map.xedges.copy(),
        errors=errors,
        name=name,
        xlabel=count_map.xlabel,
        ylabel="Weighted entries",
    )


def project_count_vs_eta(
    count_map,
    pt_mask,
    name="",
):
    values = np.sum(
        count_map.values[
            :,
            pt_mask
        ],
        axis=1,
    )

    errors = None

    if count_map.errors is not None:
        errors = np.sqrt(
            np.sum(
                count_map.errors[
                    :,
                    pt_mask
                ] ** 2,
                axis=1,
            )
        )

    return Hist1D(
        values=values,
        edges=count_map.yedges.copy(),
        errors=errors,
        name=name,
        xlabel=count_map.ylabel,
        ylabel="Weighted entries",
    )


def project_raw_response(
    response_map,
    low,
    high,
    name="",
):
    """
    Project an arbitrary pT(Z) range onto DB/MPF.

    This supports overlapping plotting categories, e.g.
        30--50,
        50--100,
        100--200,
    and also the inclusive
        30--200

    provided the stored TH2 x-axis contains the required boundaries.
    """
    pt_mask = pt_bin_mask(
        response_map,
        low,
        high,
    )

    if not np.any(pt_mask):
        raise ValueError(
            "No stored pT(Z) bins found for [{}, {}) in '{}'. "
            "Check the TH2 x-axis binning."
            .format(
                low,
                "inf" if high is None else high,
                response_map.name,
            )
        )

    values = np.sum(
        response_map.values[
            :,
            pt_mask
        ],
        axis=1,
    )

    errors = None

    if response_map.errors is not None:
        errors = np.sqrt(
            np.sum(
                response_map.errors[
                    :,
                    pt_mask
                ] ** 2,
                axis=1,
            )
        )

    return Hist1D(
        values=values,
        edges=response_map.yedges.copy(),
        errors=errors,
        name=name,
        xlabel=response_map.ylabel,
        ylabel="Weighted entries",
    )


def eta_region_label(
    low,
    high,
):
    return (
        r"${:g} \leq |\eta^{{jet}}| < {:g}$"
        .format(
            low,
            high,
        )
    )


def plot_methods(
    data_methods,
    mc_methods,
    output,
    args,
    *,
    labels,
    xlabel,
    ylabel,
    side_text=None,
    xlim=None,
    ylim=None,
    ratio_ylim=None,
    normalize_mc=False,
    logx=False,
    auto_y=True,
):
    if ratio_ylim is None:
        ratio_ylim = (
            args.ratio_min,
            args.ratio_max,
        )

    plot_hist1d_methods_data_mc(
        data_methods,
        mc_methods,
        output,
        labels=labels,
        xlabel=xlabel,
        ylabel=ylabel,
        ratio_label="Data / MC",
        normalize_mc_to_data=normalize_mc,
        xlim=xlim,
        ylim=ylim,
        auto_y=auto_y,
        ratio_ylim=ratio_ylim,
        auto_ratio_y=False,
        mc_ratio_uncertainty_band=True,
        logx=logx,
        legend_outside=True,
        ratio_legend=False,
        side_text=side_text,
        cms_label=args.cms_label,
        lumi=args.lumi,
        com=args.com,
        title=None,
    )


def load_count_maps(
    data_reader,
    mc_reader,
    region,
    methods,
):
    data = OrderedDict()
    mc = OrderedDict()

    for method in methods:
        name = (
            "Count_{}_vs_ZptEta"
            .format(method)
        )

        data[method] = get_map(
            data_reader,
            region,
            name,
        )

        mc[method] = get_map(
            mc_reader,
            region,
            name,
        )

    # All count maps are expected to carry the same fine signed-eta axis.
    if data:
        validate_fine_eta_input(
            next(iter(data.values())),
            context="Data count map",
        )

    if mc:
        validate_fine_eta_input(
            next(iter(mc.values())),
            context="MC count map",
        )

    return data, mc


def make_distributions(
    args,
    data_reader,
    mc_reader,
    output_dir,
    formats,
):
    """
    Old distribution views, now restricted to Nominal vs Windowed and to the
    three requested pT(Z) categories.
    """
    data_count, mc_count = (
        load_count_maps(
            data_reader,
            mc_reader,
            args.region,
            DISTRIBUTION_METHODS,
        )
    )

    # --------------------------------------------------------
    # Inclusive Z pT distribution.
    # --------------------------------------------------------
    data_zpt = OrderedDict()
    mc_zpt = OrderedDict()

    for method in DISTRIBUTION_METHODS:
        data_zpt[method] = (
            project_count_vs_pt(
                data_count[method],
                method,
            )
        )

        mc_zpt[method] = (
            project_count_vs_pt(
                mc_count[method],
                method,
            )
        )

    # log-x cannot display x=0, so start at the first positive profile edge.
    positive_min = float(
        data_zpt[
            next(iter(DISTRIBUTION_METHODS))
        ].edges[
            data_zpt[
                next(iter(DISTRIBUTION_METHODS))
            ].edges > 0
        ][0]
    )

    plot_methods(
        data_zpt,
        mc_zpt,
        outputs(
            output_dir
            / "distributions"
            / "Zpt",
            formats,
        ),
        args,
        labels=DISTRIBUTION_METHODS,
        xlabel=r"$p_T^Z$ [GeV]",
        ylabel="Weighted entries",
        xlim=(
            max(
                args.zpt_min,
                positive_min,
            ),
            args.zpt_max,
        ),
        normalize_mc=args.normalize_distributions,
        logx=True,
    )

    # --------------------------------------------------------
    # Jet eta + raw DB/MPF in each broad pT category.
    # --------------------------------------------------------
    raw_maps = {
        "DB": (
            OrderedDict(),
            OrderedDict(),
        ),
        "MPF": (
            OrderedDict(),
            OrderedDict(),
        ),
    }

    for observable in (
        "DB",
        "MPF",
    ):
        data_maps, mc_maps = (
            raw_maps[
                observable
            ]
        )

        for method in DISTRIBUTION_METHODS:
            name = (
                "{}Dist_{}_vs_ZptCategory"
                .format(
                    observable,
                    method,
                )
            )

            data_maps[method] = get_map(
                data_reader,
                args.region,
                name,
            )

            mc_maps[method] = get_map(
                mc_reader,
                args.region,
                name,
            )

    for category_name, (
        low,
        high,
        category_label,
    ) in PT_CATEGORIES.items():
        reference = data_count[
            next(iter(DISTRIBUTION_METHODS))
        ]

        pt_mask = pt_bin_mask(
            reference,
            low,
            high,
        )

        # fine signed eta distribution
        data_eta = OrderedDict()
        mc_eta = OrderedDict()

        for method in DISTRIBUTION_METHODS:
            data_eta[method] = (
                project_count_vs_eta(
                    data_count[method],
                    pt_mask,
                    method,
                )
            )

            mc_eta[method] = (
                project_count_vs_eta(
                    mc_count[method],
                    pt_mask,
                    method,
                )
            )

        plot_methods(
            data_eta,
            mc_eta,
            outputs(
                output_dir
                / "distributions"
                / "Jet_eta"
                / "Jet_eta_{}".format(
                    category_name
                ),
                formats,
            ),
            args,
        labels=DISTRIBUTION_METHODS,
            xlabel=r"$\eta^{jet}$",
            ylabel="Weighted entries",
            side_text=category_label,
            normalize_mc=args.normalize_distributions,
            logx=False,
        )

        # raw DB and MPF distributions
        for observable, xlabel in (
            (
                "DB",
                r"$p_T^{jet}/p_T^Z$",
            ),
            (
                "MPF",
                "MPF response",
            ),
        ):
            data_methods = OrderedDict()
            mc_methods = OrderedDict()

            data_maps, mc_maps = (
                raw_maps[
                    observable
                ]
            )

            for method in DISTRIBUTION_METHODS:
                data_methods[method] = (
                    project_raw_response(
                        data_maps[method],
                        low,
                        high,
                        method,
                    )
                )

                mc_methods[method] = (
                    project_raw_response(
                        mc_maps[method],
                        low,
                        high,
                        method,
                    )
                )

            xlim = (
                (
                    args.db_min,
                    args.db_max,
                )
                if observable == "DB"
                else (
                    args.mpf_min,
                    args.mpf_max,
                )
            )

            
            plot_methods(
                data_methods,
                mc_methods,
                outputs(
                    output_dir
                    / "distributions"
                    / observable
                    / "{}_{}".format(
                        observable,
                        category_name,
                    ),
                    formats,
                ),
                args,
        labels=DISTRIBUTION_METHODS,
                xlabel=xlabel,
                ylabel="Weighted entries",
                side_text=category_label,
                xlim=xlim,
                normalize_mc=args.normalize_distributions,
                logx=False,
            )


def make_responses_vs_pt(
    args,
    data_reader,
    mc_reader,
    output_dir,
    formats,
):
    """
    Mean DB/MPF versus pT(Z), using the six coarse |eta| categories.

    The underlying maps remain fine and signed in eta. Positive and negative
    eta bins are combined only here.
    """
    data_count, mc_count = (
        load_count_maps(
            data_reader,
            mc_reader,
            args.region,
            PROFILE_METHODS,
        )
    )

    for observable, ylabel in (
        (
            "DB",
            "Direct balance",
        ),
        (
            "MPF",
            "MPF response",
        ),
    ):
        data_profile = OrderedDict()
        mc_profile = OrderedDict()

        for method in PROFILE_METHODS:
            name = (
                "{}_{}_vs_ZptEta"
                .format(
                    observable,
                    method,
                )
            )

            data_profile[method] = get_map(
                data_reader,
                args.region,
                name,
            )

            mc_profile[method] = get_map(
                mc_reader,
                args.region,
                name,
            )

        reference = data_profile[
            next(iter(PROFILE_METHODS))
        ]

        positive_edges = (
            reference.xedges[
                reference.xedges > 0
            ]
        )

        plot_min = max(
            args.zpt_min,
            float(
                positive_edges[0]
            ),
        )

        for region_name, (
            eta_low,
            eta_high,
        ) in COARSE_ABS_ETA_REGIONS.items():
            eta_mask = abs_eta_mask(
                reference,
                eta_low,
                eta_high,
            )

            data_methods = OrderedDict()
            mc_methods = OrderedDict()

            for method in PROFILE_METHODS:
                data_methods[method] = (
                    combine_profile_bins(
                        data_profile[method],
                        data_count[method],
                        eta_mask=eta_mask,
                        output_axis="pt",
                        name=method,
                    )
                )

                mc_methods[method] = (
                    combine_profile_bins(
                        mc_profile[method],
                        mc_count[method],
                        eta_mask=eta_mask,
                        output_axis="pt",
                        name=method,
                    )
                )

            ylim = (
                (
                    args.db_min,
                    args.db_max,
                )
                if observable == "DB"
                else (
                    args.mpf_min,
                    args.mpf_max,
                )
            )

            plot_methods(
                data_methods,
                mc_methods,
                outputs(
                    output_dir
                    / "responses_vs_pt"
                    / observable
                    / "{}_{}".format(
                        observable,
                        region_name,
                    ),
                    formats,
                ),
                args,
                labels=PROFILE_METHODS,
                xlabel=r"$p_T^Z$ [GeV]",
                ylabel=ylabel,
                side_text=eta_region_label(
                    eta_low,
                    eta_high,
                ),
                xlim=(
                    plot_min,
                    args.zpt_max,
                ),
                ylim=ylim,
                ratio_ylim=(
                    args.response_ratio_min,
                    args.response_ratio_max,
                ),
                logx=True,
                auto_y=False,
            )


def make_responses_vs_eta(
    args,
    data_reader,
    mc_reader,
    output_dir,
    formats,
):
    """
    Mean DB/MPF versus the fine signed eta binning.

    Only three pT(Z) categories are produced:
        [0,20], [20,50], [>50] GeV.
    """
    data_count, mc_count = (
        load_count_maps(
            data_reader,
            mc_reader,
            args.region,
            PROFILE_METHODS,
        )
    )

    for observable, ylabel in (
        (
            "DB",
            "Direct balance",
        ),
        (
            "MPF",
            "MPF response",
        ),
    ):
        data_profile = OrderedDict()
        mc_profile = OrderedDict()

        for method in PROFILE_METHODS:
            name = (
                "{}_{}_vs_ZptEta"
                .format(
                    observable,
                    method,
                )
            )

            data_profile[method] = get_map(
                data_reader,
                args.region,
                name,
            )

            mc_profile[method] = get_map(
                mc_reader,
                args.region,
                name,
            )

        reference = data_profile[
            next(iter(PROFILE_METHODS))
        ]

        for category_name, (
            low,
            high,
            category_label,
        ) in PT_CATEGORIES.items():
            pt_mask = pt_bin_mask(
                reference,
                low,
                high,
            )

            data_methods = OrderedDict()
            mc_methods = OrderedDict()

            for method in PROFILE_METHODS:
                data_methods[method] = (
                    combine_profile_bins(
                        data_profile[method],
                        data_count[method],
                        pt_mask=pt_mask,
                        output_axis="eta",
                        name=method,
                    )
                )

                mc_methods[method] = (
                    combine_profile_bins(
                        mc_profile[method],
                        mc_count[method],
                        pt_mask=pt_mask,
                        output_axis="eta",
                        name=method,
                    )
                )

            plot_methods(
                data_methods,
                mc_methods,
                outputs(
                    output_dir
                    / "responses_vs_eta"
                    / observable
                    / "{}_{}".format(
                        observable,
                        category_name,
                    ),
                    formats,
                ),
                args,
                labels=PROFILE_METHODS,
                xlabel=r"$\eta^{jet}$",
                ylabel=ylabel,
                side_text=category_label,
                ratio_ylim=(
                    args.response_ratio_min,
                    args.response_ratio_max,
                ),
                logx=False,
                auto_y=False,
            )


def make_compositions(
    args,
    data_reader,
    mc_reader,
    output_dir,
    formats,
):
    """
    Energy-fraction composition versus pT(Z) in the six coarse |eta| regions.

    The underlying profile maps use the fine signed eta binning. The coarse
    absolute-eta average is constructed here with the matching count-map
    sum of weights.
    """
    data_count, mc_count = (
        load_count_maps(
            data_reader,
            mc_reader,
            args.region,
            FRACTION_METHODS,
        )
    )

    for method, method_label in FRACTION_METHODS.items():
        data_profiles = OrderedDict()
        mc_profiles = OrderedDict()

        for fraction in FRACTIONS:
            name = (
                "{}_{}_vs_ZptEta"
                .format(
                    fraction,
                    method,
                )
            )

            data_profiles[fraction] = get_map(
                data_reader,
                args.region,
                name,
            )

            mc_profiles[fraction] = get_map(
                mc_reader,
                args.region,
                name,
            )

        reference = data_profiles[
            next(iter(FRACTIONS))
        ]

        positive_edges = (
            reference.xedges[
                reference.xedges > 0
            ]
        )

        plot_min = max(
            args.zpt_min,
            float(
                positive_edges[0]
            ),
        )

        for region_name, (
            eta_low,
            eta_high,
        ) in COARSE_ABS_ETA_REGIONS.items():
            eta_mask = abs_eta_mask(
                reference,
                eta_low,
                eta_high,
            )

            data_components = OrderedDict()
            mc_components = OrderedDict()

            for fraction in FRACTIONS:
                data_components[fraction] = (
                    combine_profile_bins(
                        data_profiles[fraction],
                        data_count[method],
                        eta_mask=eta_mask,
                        output_axis="pt",
                        name=fraction,
                    )
                )

                mc_components[fraction] = (
                    combine_profile_bins(
                        mc_profiles[fraction],
                        mc_count[method],
                        eta_mask=eta_mask,
                        output_axis="pt",
                        name=fraction,
                    )
                )

            plot_fraction_composition_data_mc(
                data_components,
                mc_components,
                outputs(
                    output_dir
                    / "fractions"
                    / method
                    / "fractions_{}_{}".format(
                        method,
                        region_name,
                    ),
                    formats,
                ),
                labels=FRACTIONS,
                stack_order="descending",
                xlabel=r"$p_T^Z$ [GeV]",
                ylabel="Energy fraction",
                ratio_label="Data / MC",
                cms_label=args.cms_label,
                lumi=args.lumi,
                com=args.com,
                method_label=method_label,
                eta_label=eta_region_label(
                    eta_low,
                    eta_high,
                ),
                xlim=(
                    plot_min,
                    args.zpt_max,
                ),
                logx=True,
                ratio_ylim=(
                    args.fraction_ratio_min,
                    args.fraction_ratio_max,
                ),
                auto_ratio_y=False,
                mc_ratio_uncertainty_band=True,
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
        default="plots_profile2d",
    )

    parser.add_argument(
        "--region",
        default="zjet",
    )

    parser.add_argument(
        "--formats",
        default="png",
    )

    parser.add_argument(
        "--only",
        choices=(
            "all",
            "distributions",
            "responses-vs-pt",
            "responses-vs-eta",
            "fractions",
        ),
        default="all",
    )

    parser.add_argument(
        "--zpt-min",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--zpt-max",
        type=float,
        default=3103.0,
    )

    parser.add_argument(
        "--ratio-min",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--ratio-max",
        type=float,
        default=1.5,
    )

    parser.add_argument(
        "--response-ratio-min",
        type=float,
        default=0.8,
    )

    parser.add_argument(
        "--response-ratio-max",
        type=float,
        default=1.2,
    )

    parser.add_argument(
        "--fraction-ratio-min",
        type=float,
        default=0.8,
    )

    parser.add_argument(
        "--fraction-ratio-max",
        type=float,
        default=1.2,
    )

    parser.add_argument(
        "--db-min",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--db-max",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--mpf-min",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--mpf-max",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--normalize-distributions",
        dest="normalize_distributions",
        action="store_true",
        default=True,
        help=(
            "Normalize MC to the Data integral separately for each "
            "distribution and method (default)."
        ),
    )

    parser.add_argument(
        "--no-normalize-distributions",
        dest="normalize_distributions",
        action="store_false",
        help=(
            "Keep the absolute weighted MC normalization in distribution "
            "plots."
        ),
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

    args = parser.parse_args()

    formats = parse_formats(
        args.formats
    )

    output_dir = Path(
        args.output_dir
    )

    with RootFileReader(
        args.data
    ) as data_reader, RootFileReader(
        args.mc
    ) as mc_reader:

        if args.only in (
            "all",
            "distributions",
        ):
            make_distributions(
                args,
                data_reader,
                mc_reader,
                output_dir,
                formats,
            )

        if args.only in (
            "all",
            "responses-vs-pt",
        ):
            make_responses_vs_pt(
                args,
                data_reader,
                mc_reader,
                output_dir,
                formats,
            )

        if args.only in (
            "all",
            "responses-vs-eta",
        ):
            make_responses_vs_eta(
                args,
                data_reader,
                mc_reader,
                output_dir,
                formats,
            )

        if args.only in (
            "all",
            "fractions",
        ):
            make_compositions(
                args,
                data_reader,
                mc_reader,
                output_dir,
                formats,
            )


if __name__ == "__main__":
    main()
