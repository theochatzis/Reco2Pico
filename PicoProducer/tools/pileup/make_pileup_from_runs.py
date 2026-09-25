#!/usr/bin/env python3

import argparse
import glob
import json
import os
import re
from array import array
from pathlib import Path

import ROOT

ROOT.gROOT.SetBatch(True)

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def expand_files(patterns, use_regex=False, search_dir="."):
    files = []

    if use_regex:
        regexes = [re.compile(p) for p in patterns]

        for path in Path(search_dir).rglob("*.root"):
            name = str(path)
            rel = os.path.relpath(name, search_dir)

            if any(r.search(name) or r.search(rel) for r in regexes):
                files.append(name)

    else:
        for pattern in patterns:
            matches = glob.glob(pattern, recursive=True)

            if not matches and os.path.isfile(pattern):
                matches = [pattern]

            files.extend(matches)

    files = sorted(set(files))

    if not files:
        raise RuntimeError("No ROOT files matched the input pattern(s).")

    return files


def read_schema(filename, schema_name="bookkeepingSchema"):
    f = ROOT.TFile.Open(filename, "READ")

    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open {filename}")

    try:
        obj = f.Get(schema_name)

        if not obj:
            raise RuntimeError(
                f"Could not find '{schema_name}' in {filename}"
            )

        if not obj.InheritsFrom("TObjString"):
            raise RuntimeError(
                f"'{schema_name}' in {filename} is not a TObjString"
            )

        return json.loads(obj.GetString().Data())

    finally:
        f.Close()


def get_pileup_definition(schema):
    try:
        cfg = schema["histograms"]["pileup"]
    except KeyError as exc:
        raise RuntimeError(
            "bookkeepingSchema has no histograms -> pileup entry"
        ) from exc

    contents = cfg["contents"]
    edges = [float(x) for x in cfg["edges"]]
    flow_bins = bool(cfg.get("flow_bins", False))

    if len(edges) < 2:
        raise RuntimeError("Pileup binning has fewer than two edges")

    if any(b <= a for a, b in zip(edges[:-1], edges[1:])):
        raise RuntimeError("Pileup bin edges are not strictly increasing")

    return cfg, contents, edges, flow_bins


def check_metadata(files, schema_name):
    reference = None
    reference_schema = None

    iterator = files

    if tqdm is not None:
        iterator = tqdm(
            files,
            desc="Checking metadata",
            unit="file",
        )

    for filename in iterator:
        schema = read_schema(filename, schema_name)
        cfg, contents, edges, flow_bins = get_pileup_definition(schema)

        current = {
            "contents": contents,
            "edges": edges,
            "flow_bins": flow_bins,
            "variable": cfg.get("variable"),
            "weight": cfg.get("weight"),
            "mantissa_bits": cfg.get("mantissa_bits"),
        }

        if reference is None:
            reference = current
            reference_schema = schema
            continue

        if current != reference:
            raise RuntimeError(
                "Input files do not use the same pileup bookkeeping schema.\n"
                f"Reference:\n{json.dumps(reference, indent=2)}\n"
                f"Different file: {filename}\n"
                f"Found:\n{json.dumps(current, indent=2)}"
            )

    return reference_schema, reference


def make_runs_chain(files):
    chain = ROOT.TChain("Runs")

    iterator = files

    if tqdm is not None:
        iterator = tqdm(
            files,
            desc="Building Runs chain",
            unit="file",
        )

    for filename in iterator:
        if chain.Add(filename) == 0:
            raise RuntimeError(
                f"Could not add Runs tree from {filename}"
            )

    if chain.GetEntries() == 0:
        raise RuntimeError("Runs TChain has zero entries")

    return chain


def build_pileup_hist(chain, contents_branch, edges, flow_bins):
    n_bins = len(edges) - 1

    expected_size = (
        n_bins + 2
        if flow_bins
        else n_bins
    )

    count_branch = f"n{contents_branch}"

    if not chain.GetBranch(contents_branch):
        raise RuntimeError(
            f"Runs branch '{contents_branch}' not found"
        )

    if not chain.GetBranch(count_branch):
        raise RuntimeError(
            f"Runs branch '{count_branch}' not found"
        )

    h = ROOT.TH1D(
        "pileup",
        "True pileup distribution;Pileup_nTrueInt;#Sigma genWeight",
        n_bins,
        array("d", edges),
    )

    h.SetDirectory(0)

    total_gen_sumw = 0.0
    total_gen_count = 0

    has_sumw = bool(chain.GetBranch("genEventSumw"))
    has_count = bool(chain.GetBranch("genEventCount"))

    n_entries = chain.GetEntries()
    iterator = range(n_entries)

    if tqdm is not None:
        iterator = tqdm(
            iterator,
            total=n_entries,
            desc="Summing Runs",
            unit="entry",
        )

    for ientry in iterator:
        chain.GetEntry(ientry)

        n_values = int(
            getattr(chain, count_branch)
        )

        if n_values != expected_size:
            raise RuntimeError(
                f"Runs entry {ientry}: {count_branch} = {n_values}, "
                f"expected {expected_size} from metadata"
            )

        values = getattr(
            chain,
            contents_branch,
        )

        if flow_bins:
            # index 0 = underflow
            # 1..N = regular bins
            # N+1 = overflow
            for i in range(n_values):
                h.AddBinContent(
                    i,
                    float(values[i]),
                )
        else:
            for i in range(n_values):
                h.AddBinContent(
                    i + 1,
                    float(values[i]),
                )

        if has_sumw:
            total_gen_sumw += float(
                chain.genEventSumw
            )

        if has_count:
            total_gen_count += int(
                chain.genEventCount
            )

    return h, total_gen_sumw, total_gen_count


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a ROOT histogram named 'pileup' from Reco2Pico "
            "Runs.pileupSumw across many files."
        )
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help=(
            "ROOT files or glob patterns, e.g. 'picos/*.root'. "
            "Use --regex to interpret them as regular expressions."
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        default="pileup.root",
        help="Output ROOT file (default: pileup.root)",
    )

    parser.add_argument(
        "--regex",
        action="store_true",
        help="Interpret input patterns as regular expressions",
    )

    parser.add_argument(
        "--search-dir",
        default=".",
        help=(
            "Directory searched recursively in --regex mode "
            "(default: current directory)"
        ),
    )

    parser.add_argument(
        "--schema-name",
        default="bookkeepingSchema",
        help="Name of the bookkeeping JSON TObjString",
    )

    args = parser.parse_args()

    files = expand_files(
        args.inputs,
        use_regex=args.regex,
        search_dir=args.search_dir,
    )

    print(f"\nMatched {len(files)} ROOT file(s)")

    schema, definition = check_metadata(
        files,
        args.schema_name,
    )

    contents = definition["contents"]
    edges = definition["edges"]
    flow_bins = definition["flow_bins"]

    print("\nPileup schema")
    print(f"  contents branch : {contents}")
    print(f"  regular bins    : {len(edges) - 1}")
    print(f"  range           : {edges[0]} -> {edges[-1]}")
    print(f"  flow bins       : {flow_bins}")

    chain = make_runs_chain(files)

    print(
        f"  Runs entries    : {chain.GetEntries()}"
    )

    pileup, total_sumw, total_count = build_pileup_hist(
        chain,
        contents,
        edges,
        flow_bins,
    )

    integral = pileup.Integral(
        0,
        pileup.GetNbinsX() + 1,
    )

    print("\nSummary")
    print(
        f"  pileup integral incl. flow : {integral:.12g}"
    )

    if chain.GetBranch("genEventSumw"):
        print(
            f"  sum Runs.genEventSumw       : {total_sumw:.12g}"
        )
        print(
            f"  difference                  : "
            f"{integral - total_sumw:+.12g}"
        )

    if chain.GetBranch("genEventCount"):
        print(
            f"  sum Runs.genEventCount      : {total_count}"
        )

    output = ROOT.TFile.Open(
        args.output,
        "RECREATE",
    )

    if not output or output.IsZombie():
        raise RuntimeError(
            f"Could not create {args.output}"
        )

    pileup.Write(
        "pileup",
        ROOT.TObject.kOverwrite,
    )

    # Keep the metadata too so the derived ROOT file remains self-describing.
    metadata = ROOT.TObjString(
        json.dumps(
            schema,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    metadata.Write(
        args.schema_name,
        ROOT.TObject.kOverwrite,
    )

    output.Close()

    print(
        f"\nSaved histogram 'pileup' to {args.output}"
    )


if __name__ == "__main__":
    main()
