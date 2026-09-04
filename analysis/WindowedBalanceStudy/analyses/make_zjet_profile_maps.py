#!/usr/bin/env python3

"""
Compact histogram configuration for the Z+jet windowed study.

Plotting method sets
--------------------

Distributions:
    parallel
    transverse
    windowed

Responses/composition:
    nominal
    windowed

Stored maps
-----------

Count maps:
    nominal, parallel, transverse, windowed

Profile maps:
    nominal, windowed only

Raw DB/MPF shape maps:
    parallel, transverse, windowed only
"""

import argparse
from collections import OrderedDict
from pathlib import Path

import numpy as np
import yaml


# ============================================================
# pT(Z)
# ============================================================

PTZ_EDGES = [
    0, 3, 5, 6, 9, 12, 15,
    20, 28, 30, 37, 50, 59, 86,
    100, 110, 132, 170, 200, 204, 236, 279,
    302, 373, 460, 575, 638, 737,
    846, 967, 1101, 1248, 1410, 1588,
    1784, 2000, 2238, 2500, 2787, 3103,
    7000,
]

PT_CATEGORY_EDGES = [
    5.0,
    15.0,
    30.0,
    50.0,
    100.0,
    200.0,
    7000.0
]

# ============================================================
#  Jet pT bins
# ============================================================

JET_PT_EDGES = [
    0, 2, 4, 6, 8, 10,
    12, 15, 20, 25, 30,
    40, 50, 60, 80, 100,
    150, 200, 300, 500,
]

# ============================================================
# Fine signed eta binning, close to the HCAL tower segmentation.
#
# The central detector uses ~0.087-wide eta towers, with progressively
# wider bins toward the forward region.  We also insert the exact coarse
# analysis boundaries (1.3, 1.5, 2.7, 3.0, 5.0) so later |eta| merging is
# exact rather than approximate.
# ============================================================

_BASE_POSITIVE_ETA_EDGES = [
    0.000,
    0.087,
    0.174,
    0.261,
    0.348,
    0.435,
    0.522,
    0.609,
    0.696,
    0.783,
    0.879,
    0.957,
    1.044,
    1.131,
    1.218,
    1.305,
    1.392,
    1.479,
    1.566,
    1.653,
    1.740,
    1.830,
    1.930,
    2.043,
    2.172,
    2.322,
    2.500,
    2.650,
    2.853,
    2.964,
    3.139,
    3.314,
    3.489,
    3.664,
    3.839,
    4.013,
    4.191,
    4.363,
    4.538,
    4.716,
    4.889,
    5.191,
]

_ANALYSIS_ETA_BOUNDARIES = [
    1.3,
    1.5,
    2.7,
    3.0,
    5.0,
]

POSITIVE_ETA_EDGES = sorted(
    set(
        _BASE_POSITIVE_ETA_EDGES
        + _ANALYSIS_ETA_BOUNDARIES
    )
)

ETA_EDGES = (
    [
        -value
        for value in reversed(
            POSITIVE_ETA_EDGES[1:]
        )
    ]
    + POSITIVE_ETA_EDGES
)


# The coarse absolute-eta regions used for response-vs-pT and composition.
COARSE_ABS_ETA_REGIONS = OrderedDict([
    ("eta0to1p3",   (0.0, 1.3)),
    ("eta1p3to1p5", (1.3, 1.5)),
    ("eta1p5to2p5", (1.5, 2.5)),
    ("eta2p5to2p7", (2.5, 2.7)),
    ("eta2p7to3p0", (2.7, 3.0)),
    ("eta3p0to5p0", (3.0, 5.0)),
])


RESPONSE_METHODS = OrderedDict([
    ("nominal", "nominal"),
    ("windowed", "windowed / subtracted"),
])

FRACTION_METHODS = OrderedDict([
    ("nominal", "nominal"),
    ("parallel", "parallel / signal"),
    ("transverse", "transverse control"),
    ("windowed", "windowed / subtracted"),
])

DISTRIBUTION_METHODS = OrderedDict([
    ("parallel", "parallel / signal"),
    ("transverse", "transverse control"),
    ("windowed", "windowed / subtracted"),
])

# Count maps are needed by all plotting views.
COUNT_METHODS = OrderedDict([
    ("nominal", "nominal"),
    ("parallel", "parallel / signal"),
    ("transverse", "transverse control"),
    ("windowed", "windowed / subtracted"),
])


RESPONSE_VARIABLES = OrderedDict([
    ("DB", "Direct balance"),
    ("MPF", "MPF"),
])

FRACTION_VARIABLES = OrderedDict([
    ("chHEF", "Charged-hadron energy fraction"),
    ("neHEF", "Neutral-hadron energy fraction"),
    ("chEmEF", "Charged EM energy fraction"),
    ("neEmEF", "Neutral EM energy fraction"),
    ("muEF", "Muon energy fraction"),
])


def uniform_edges(nbins, xmin, xmax):
    return [
        float(value)
        for value in np.linspace(
            float(xmin),
            float(xmax),
            int(nbins) + 1,
        )
    ]


DB_EDGES = uniform_edges(
    120,
    0.0,
    2.4,
)

MPF_EDGES = uniform_edges(
    160,
    -1.0,
    3.0,
)


class FlowList(list):
    pass


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    FlowList,
    lambda dumper, value: dumper.represent_sequence(
        "tag:yaml.org,2002:seq",
        value,
        flow_style=True,
    ),
)

Dumper.add_representer(
    OrderedDict,
    lambda dumper, value: dumper.represent_dict(
        value.items()
    ),
)


def flow(values):
    return FlowList(values)


def method_columns(method):
    if method == "nominal":
        return {
            "zpt": "Z_pt_nominal",
            "eta": "Jet_eta_nominal",
            "jet_pt": "Probe_pt_nominal_vec",
            "weight": "weight_nominal",
            "DB": "DB_nominal_vec",
            "MPF": "MPF_nominal_vec",
            "chHEF": "Jet_chHEF_nominal",
            "neHEF": "Jet_neHEF_nominal",
            "chEmEF": "Jet_chEmEF_nominal",
            "neEmEF": "Jet_neEmEF_nominal",
            "muEF": "Jet_muEF_nominal",
        }

    return {
        "zpt": "Z_pt_{}".format(
            method
        ),
        "eta": "Jet_eta_{}".format(
            method
        ),
        "jet_pt": "Jet_pt_{}".format(
            method
        ),
        "weight": "weight_{}".format(
            method
        ),
        "DB": "DB_{}".format(
            method
        ),
        "MPF": "MPF_{}".format(
            method
        ),
        "chHEF": "Jet_chHEF_{}".format(
            method
        ),
        "neHEF": "Jet_neHEF_{}".format(
            method
        ),
        "chEmEF": "Jet_chEmEF_{}".format(
            method
        ),
        "neEmEF": "Jet_neEmEF_{}".format(
            method
        ),
        "muEF": "Jet_muEF_{}".format(
            method
        ),
    }


def th1(
    title,
    variable,
    weight,
    *,
    bins=None,
    edges=None,
):
    result = OrderedDict()
    result["title"] = title

    if edges is not None:
        result["edges"] = flow(
            edges
        )
    else:
        result["bins"] = flow(
            bins
        )

    result["variable"] = variable
    result["weight"] = weight

    return result


def count2d(
    title,
    x,
    y,
    weight,
):
    return OrderedDict([
        ("type", "TH2D"),
        ("title", title),
        ("edges_x", flow(PTZ_EDGES)),
        ("edges_y", flow(ETA_EDGES)),
        ("variable_x", x),
        ("variable_y", y),
        ("weight", weight),
    ])


def profile2d(
    title,
    x,
    y,
    z,
    weight,
):
    return OrderedDict([
        ("type", "TProfile2D"),
        ("title", title),
        ("edges_x", flow(PTZ_EDGES)),
        ("edges_y", flow(ETA_EDGES)),
        ("variable_x", x),
        ("variable_y", y),
        ("variable_z", z),
        ("weight", weight),
    ])

def jet_pt_dist2d(
    title,
    x,
    y,
    weight,
):
    return OrderedDict([
        ("type", "TH2D"),
        ("title", title),
        ("edges_x", flow(PTZ_EDGES)),
        ("edges_y", flow(JET_PT_EDGES)),
        ("variable_x", x),
        ("variable_y", y),
        ("weight", weight),
    ])

def raw_response2d(
    title,
    x,
    y,
    weight,
    yedges,
):
    return OrderedDict([
        ("type", "TH2D"),
        ("title", title),
        ("edges_x", flow(PT_CATEGORY_EDGES)),
        ("edges_y", flow(yedges)),
        ("variable_x", x),
        ("variable_y", y),
        ("weight", weight),
    ])


def generate():
    histograms = OrderedDict()

    # Small event-level sanity set.
    histograms["Z_mass"] = th1(
        "Z mass;m_{#mu#mu} [GeV];Events",
        "Z_mass",
        "zjet_eventWeight",
        bins=[80, 80, 102],
    )

    histograms["Z_pt"] = th1(
        "Z p_{T};p_{T}^{Z} [GeV];Events",
        "Z_pt",
        "zjet_eventWeight",
        edges=PTZ_EDGES,
    )

    histograms["PV_npvs"] = th1(
        "Number of primary vertices;N_{PV};Events",
        "PV_npvs",
        "zjet_eventWeight",
        bins=[100, 0, 100],
    )

    # Count maps for every method used anywhere in plotting.
    for method, description in COUNT_METHODS.items():
        columns = method_columns(
            method
        )

        histograms[
            "Count_{}_vs_ZptEta".format(
                method
            )
        ] = count2d(
            "Weighted entries, {};p_{{T}}^{{Z}} [GeV];#eta^{{jet}}"
            .format(
                description
            ),
            columns["zpt"],
            columns["eta"],
            columns["weight"],
        )

    # DB/MPF response maps: only Nominal and Windowed.
    for method, description in RESPONSE_METHODS.items():
        columns = method_columns(
            method
        )

        for observable, title in RESPONSE_VARIABLES.items():
            histograms[
                "{}_{}_vs_ZptEta".format(
                    observable,
                    method,
                )
            ] = profile2d(
                "<{}>, {};p_{{T}}^{{Z}} [GeV];#eta^{{jet}};{}"
                .format(
                    title,
                    description,
                    title,
                ),
                columns["zpt"],
                columns["eta"],
                columns[observable],
                columns["weight"],
            )

    # Energy-fraction maps: all four physics methods.
    for method, description in FRACTION_METHODS.items():
        columns = method_columns(
            method
        )

        for observable, title in FRACTION_VARIABLES.items():
            histograms[
                "{}_{}_vs_ZptEta".format(
                    observable,
                    method,
                )
            ] = profile2d(
                "<{}>, {};p_{{T}}^{{Z}} [GeV];#eta^{{jet}};{}"
                .format(
                    title,
                    description,
                    title,
                ),
                columns["zpt"],
                columns["eta"],
                columns[observable],
                columns["weight"],
            )

    # Raw DB/MPF distributions only for Parallel/Transverse/Windowed.
    for method, description in DISTRIBUTION_METHODS.items():
        columns = method_columns(
            method
        )

        histograms[
            "DBDist_{}_vs_ZptCategory".format(
                method
            )
        ] = raw_response2d(
            "DB distribution, {};p_{{T}}^{{Z}} [GeV];DB"
            .format(
                description
            ),
            columns["zpt"],
            columns["DB"],
            columns["weight"],
            DB_EDGES,
        )

        histograms[
            "MPFDist_{}_vs_ZptCategory".format(
                method
            )
        ] = raw_response2d(
            "MPF distribution, {};p_{{T}}^{{Z}} [GeV];MPF"
            .format(
                description
            ),
            columns["zpt"],
            columns["MPF"],
            columns["weight"],
            MPF_EDGES,
        )
    
    # Jet pt and Z pt in eta regions
    for method, description in DISTRIBUTION_METHODS.items():
        columns = method_columns(method)

        for region_name, (
            eta_low,
            eta_high,
        ) in COARSE_ABS_ETA_REGIONS.items():

            histograms[
                "JetPtDist_{}_{}_vs_Zpt".format(
                    method,
                    region_name,
                )
            ] = jet_pt_dist2d(
                "Jet pT, {}, {} <= |eta| < {};pT(Z) [GeV];pT(jet) [GeV]"
                .format(
                    description,
                    eta_low,
                    eta_high,
                ),
                "Z_pt_{}_{}".format(
                    method,
                    region_name,
                ),
                "Jet_pt_{}_{}".format(
                    method,
                    region_name,
                ),
                "weight_{}_{}".format(
                    method,
                    region_name,
                ),
            )
    return histograms


def write(output):
    output = Path(
        output
    )

    header = """\
# ============================================================
# AUTO-GENERATED COMPACT PROFILE-MAP CONFIGURATION
#
# Distributions: parallel / transverse / windowed
# Responses: nominal / windowed
# Fractions: nominal / parallel / transverse / windowed
#
# Fine HCAL-tower-like signed eta binning:
#   {eta}
# ============================================================

""".format(
        eta=ETA_EDGES,
    )

    body = yaml.dump(
        generate(),
        Dumper=Dumper,
        sort_keys=False,
        default_flow_style=False,
        width=100000,
    )

    output.write_text(
        header + body
    )

    return output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(__file__).resolve().parent
            / "zjet_histograms.yaml"
        ),
    )

    args = parser.parse_args()

    output = write(
        args.output
    )

    print(
        "Wrote {}".format(
            output
        )
    )

    print(
        "Definitions: {}".format(
            len(generate())
        )
    )


if __name__ == "__main__":
    main()
