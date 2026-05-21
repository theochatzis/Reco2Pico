#!/usr/bin/env python3
import argparse
from pathlib import Path
import ROOT
import yaml


def main():
    parser = argparse.ArgumentParser(description="Example RDataFrame analysis for Reco2Pico")
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True, nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    threads = int(cfg.get("threads", 0))
    if threads > 0:
        ROOT.EnableImplicitMT(threads)

    df = ROOT.RDataFrame(cfg.get("tree", "Events"), args.input)
    if cfg.get("selection"):
        df = df.Filter(cfg["selection"], "analysis selection")

    histos = []
    for hcfg in cfg.get("histograms", []):
        if "define" in hcfg:
            df = df.Define(hcfg["define"]["name"], hcfg["define"]["expression"])
        nbins, xmin, xmax = hcfg["bins"]
        histos.append(df.Histo1D((hcfg["name"], hcfg["title"], int(nbins), float(xmin), float(xmax)), hcfg["column"]))

    fout = ROOT.TFile(args.output, "RECREATE")
    for h in histos:
        h.Write()
    fout.Close()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
