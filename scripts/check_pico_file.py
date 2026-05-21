#!/usr/bin/env python3
import argparse
import ROOT
parser = argparse.ArgumentParser(description="Print basic PicoAOD file content")
parser.add_argument("file")
parser.add_argument("--tree", default="Events")
args = parser.parse_args()
f = ROOT.TFile.Open(args.file)
if not f or f.IsZombie():
    raise SystemExit(f"Could not open {args.file}")
t = f.Get(args.tree)
if not t:
    raise SystemExit(f"Could not find tree {args.tree}")
print(f"{args.file}:{args.tree}")
print(f"Entries: {t.GetEntries()}")
for b in t.GetListOfBranches():
    print("  " + b.GetName())
