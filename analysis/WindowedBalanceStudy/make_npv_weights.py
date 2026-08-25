#!/usr/bin/env python3

"""
Build NPV shape weights from the selected zjet-region PV_npvs histograms.

Workflow:
  1. Run data and MC once without NPV reweighting.
  2. Ensure zjet_histograms.yaml contains PV_npvs.
  3. Run this script.
  4. Put the produced JSON in analysis_config.yaml.
  5. Rerun MC. Data remains unweighted.
"""

import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "SkimRDFAnalysisBase"
sys.path.insert(0, str(BASE))

from plotting import (  # noqa: E402
    read_root_object,
    derive_hist1d_weights,
    save_weights_json,
    plot_hist1d_data_mc,
)
from plotting.objects import Hist1D  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Unweighted data histogram ROOT file")
    parser.add_argument("--mc", required=True, help="Unweighted MC histogram ROOT file")
    parser.add_argument(
        "--object",
        default="zjet/PV_npvs",
        help="NPV histogram path in the ROOT files",
    )
    parser.add_argument("--output", default="npv_weights.json")
    parser.add_argument("--plot", default="npv_reweighting.pdf")
    parser.add_argument("--max-weight", type=float, default=5.0)
    parser.add_argument("--cms-label", default="Preliminary")
    parser.add_argument("--lumi", type=float, default=None)
    parser.add_argument("--com", type=float, default=13.6)
    args = parser.parse_args()

    data = read_root_object(args.data, args.object)
    mc = read_root_object(args.mc, args.object)

    if not isinstance(data, Hist1D) or not isinstance(mc, Hist1D):
        raise TypeError("NPV source object must be a TH1/TProfile-like histogram.")

    payload = derive_hist1d_weights(
        data,
        mc,
        normalize=True,
        clip=(0.0, args.max_weight),
    )
    save_weights_json(payload, args.output)

    # Diagnostic shape comparison before applying the weights.
    plot_hist1d_data_mc(
        data,
        mc,
        args.plot,
        xlabel="Number of primary vertices",
        ylabel="Normalized events",
        normalize=True,
        ratio_ylim=(0.0, args.max_weight),
        cms_label=args.cms_label,
        lumi=args.lumi,
        com=args.com,
        title="",
    )

    print(f"Wrote NPV weights: {args.output}")
    print(f"Wrote diagnostic plot: {args.plot}")


if __name__ == "__main__":
    main()
