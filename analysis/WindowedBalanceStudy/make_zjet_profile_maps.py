#!/usr/bin/env python3

"""
Generate the compact Z+jet profile-map histogram configuration.

Per method (nominal, parallel, transverse, windowed):

    Count(pT(Z), |eta_jet|)           TH2D
    <DB>(pT(Z), |eta_jet|)            TProfile2D
    <MPF>(pT(Z), |eta_jet|)           TProfile2D

    <chHEF>(pT(Z), |eta_jet|)         TProfile2D
    <neHEF>(pT(Z), |eta_jet|)         TProfile2D
    <chEmEF>(pT(Z), |eta_jet|)        TProfile2D
    <neEmEF>(pT(Z), |eta_jet|)        TProfile2D
    <muEF>(pT(Z), |eta_jet|)          TProfile2D

The plotting code performs all coarse-eta and pT(Z) slicing.
"""

import argparse
from collections import OrderedDict
from pathlib import Path

import yaml


PTZ_EDGES = [
    0, 3, 6, 9, 12, 15,
    21, 28, 37, 49, 59, 86,
    110, 132, 170, 204, 236, 279,
    302, 373, 460, 575, 638, 737,
    846, 967, 1101, 1248, 1410, 1588,
    1784, 2000, 2238, 2500, 2787, 3103,
]

ABS_ETA_EDGES = [
    0.0,
    1.3,
    1.5,
    2.5,
    2.7,
    3.0,
    5.0,
]

METHODS = OrderedDict([
    ("nominal", "nominal"),
    ("parallel", "parallel / signal"),
    ("transverse", "transverse control"),
    ("windowed", "windowed / subtracted"),
])

PROFILE_VARIABLES = OrderedDict([
    ("DB", "Direct balance"),
    ("MPF", "MPF"),
    ("chHEF", "Charged-hadron energy fraction"),
    ("neHEF", "Neutral-hadron energy fraction"),
    ("chEmEF", "Charged EM energy fraction"),
    ("neEmEF", "Neutral EM energy fraction"),
    ("muEF", "Muon energy fraction"),
])


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
            "eta": "Jet_abseta_nominal",
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
        "zpt": "Z_pt_{}".format(method),
        "eta": "Jet_abseta_{}".format(method),
        "weight": "weight_{}".format(method),
        "DB": "DB_{}".format(method),
        "MPF": "MPF_{}".format(method),
        "chHEF": "Jet_chHEF_{}".format(method),
        "neHEF": "Jet_neHEF_{}".format(method),
        "chEmEF": "Jet_chEmEF_{}".format(method),
        "neEmEF": "Jet_neEmEF_{}".format(method),
        "muEF": "Jet_muEF_{}".format(method),
    }


def count2d(title, x, y, weight):
    return OrderedDict([
        ("type", "TH2D"),
        ("title", title),
        ("edges_x", flow(PTZ_EDGES)),
        ("edges_y", flow(ABS_ETA_EDGES)),
        ("variable_x", x),
        ("variable_y", y),
        ("weight", weight),
    ])


def profile2d(title, x, y, z, weight):
    return OrderedDict([
        ("type", "TProfile2D"),
        ("title", title),
        ("edges_x", flow(PTZ_EDGES)),
        ("edges_y", flow(ABS_ETA_EDGES)),
        ("variable_x", x),
        ("variable_y", y),
        ("variable_z", z),
        ("weight", weight),
    ])


def generate():
    histograms = OrderedDict()

    # Only a few event-level sanity plots.
    histograms["Z_mass"] = OrderedDict([
        ("title", "Z mass;m_{#mu#mu} [GeV];Events"),
        ("bins", flow([80, 80, 102])),
        ("variable", "Z_mass"),
        ("weight", "zjet_eventWeight"),
    ])

    histograms["Z_pt"] = OrderedDict([
        ("title", "Z p_{T};p_{T}^{Z} [GeV];Events"),
        ("edges", flow(PTZ_EDGES)),
        ("variable", "Z_pt"),
        ("weight", "zjet_eventWeight"),
    ])

    histograms["PV_npvs"] = OrderedDict([
        ("title", "Number of primary vertices;N_{PV};Events"),
        ("bins", flow([100, 0, 100])),
        ("variable", "PV_npvs"),
        ("weight", "zjet_eventWeight"),
    ])

    for method, description in METHODS.items():
        columns = method_columns(
            method
        )

        histograms[
            "Count_{}_vs_ZptEta".format(
                method
            )
        ] = count2d(
            "Weighted entries, {};p_{{T}}^{{Z}} [GeV];|#eta^{{jet}}|"
            .format(description),
            columns["zpt"],
            columns["eta"],
            columns["weight"],
        )

        for observable, title in PROFILE_VARIABLES.items():
            histograms[
                "{}_{}_vs_ZptEta".format(
                    observable,
                    method,
                )
            ] = profile2d(
                "<{}>, {};p_{{T}}^{{Z}} [GeV];|#eta^{{jet}}|;{}"
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

    return histograms


def write(output):
    output = Path(output)

    header = """\
# ============================================================
# AUTO-GENERATED COMPACT PROFILE-MAP CONFIGURATION
#
# Edit make_zjet_profile_maps.py, not this YAML.
#
# pT(Z) edges:
#   {pt}
#
# coarse |eta_jet| edges:
#   {eta}
# ============================================================

""".format(
        pt=PTZ_EDGES,
        eta=ABS_ETA_EDGES,
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
