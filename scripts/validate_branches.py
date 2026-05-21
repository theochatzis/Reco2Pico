#!/usr/bin/env python3
import argparse
import sys
import ROOT


def main():
    parser = argparse.ArgumentParser(description="Validate that PicoAOD branches exist")
    parser.add_argument("file")
    parser.add_argument("--tree", default="Events")
    parser.add_argument("--branches", nargs="+", required=True)
    args = parser.parse_args()

    f = ROOT.TFile.Open(args.file)
    if not f or f.IsZombie():
        raise SystemExit(f"Could not open {args.file}")
    t = f.Get(args.tree)
    if not t:
        raise SystemExit(f"Could not find tree {args.tree}")
    existing = {b.GetName() for b in t.GetListOfBranches()}
    missing = [b for b in args.branches if b not in existing]
    if missing:
        print("Missing branches:")
        for b in missing:
            print(f"  - {b}")
        return 1
    print("All requested branches are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
