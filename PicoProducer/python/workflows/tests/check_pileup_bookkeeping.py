#!/usr/bin/env python3

import argparse
import json
import math
from array import array

import ROOT
ROOT.gROOT.SetBatch(True)

def get_schema(root_file, object_name="bookkeepingSchema"):
    obj = root_file.Get(object_name)

    if not obj:
        raise RuntimeError(
            f"Could not find top-level metadata object '{object_name}'"
        )

    if not obj.InheritsFrom("TObjString"):
        raise RuntimeError(
            f"'{object_name}' exists but is not a TObjString "
            f"(class = {obj.ClassName()})"
        )

    text = obj.GetString().Data()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not decode JSON from '{object_name}': {exc}"
        ) from exc


def make_hist(name, title, edges):
    edge_array = array("f", edges)

    hist = ROOT.TH1D(
        name,
        title,
        len(edges) - 1,
        edge_array,
    )

    hist.Sumw2()
    hist.SetDirectory(0)

    return hist


def read_runs_pileup(root_file, schema):
    runs = root_file.Get("Runs")

    if not runs:
        raise RuntimeError("Could not find the Runs tree")

    try:
        pu_cfg = schema["histograms"]["pileup"]
    except KeyError as exc:
        raise RuntimeError(
            "bookkeepingSchema does not contain histograms -> pileup"
        ) from exc

    contents_branch = pu_cfg["contents"]
    edges = [float(x) for x in pu_cfg["edges"]]
    flow_bins = bool(pu_cfg.get("flow_bins", False))

    if len(edges) < 2:
        raise RuntimeError("Pileup metadata has fewer than two bin edges")

    n_regular_bins = len(edges) - 1
    expected_storage_bins = (
        n_regular_bins + 2
        if flow_bins
        else n_regular_bins
    )

    count_branch = f"n{contents_branch}"

    if not runs.GetBranch(contents_branch):
        raise RuntimeError(
            f"Runs branch '{contents_branch}' not found"
        )

    if not runs.GetBranch(count_branch):
        raise RuntimeError(
            f"Runs count branch '{count_branch}' not found"
        )

    hist = make_hist(
        "pileup_from_runs",
        "Pileup comparison;Pileup_nTrueInt;Weighted events",
        edges,
    )

    total_gen_sumw = 0.0
    has_gen_sumw = bool(runs.GetBranch("genEventSumw"))

    print("\n=== Runs bookkeeping ===")
    print(f"contents branch : {contents_branch}")
    print(f"count branch    : {count_branch}")
    print(f"regular bins    : {n_regular_bins}")
    print(f"stored values   : {expected_storage_bins}")
    print(f"flow bins       : {flow_bins}")
    print(f"first edge      : {edges[0]}")
    print(f"last edge       : {edges[-1]}")
    print(f"Runs entries    : {runs.GetEntries()}")

    for ientry, run_entry in enumerate(runs):
        n_stored = int(
            getattr(run_entry, count_branch)
        )

        if n_stored != expected_storage_bins:
            raise RuntimeError(
                f"Runs entry {ientry}: {count_branch} = {n_stored}, "
                f"but metadata implies {expected_storage_bins} values"
            )

        values = getattr(
            run_entry,
            contents_branch,
        )

        if flow_bins:
            # storage index 0            -> ROOT underflow bin 0
            # storage indices 1..N       -> ROOT regular bins 1..N
            # storage index N+1          -> ROOT overflow bin N+1
            for storage_bin in range(n_stored):
                hist.AddBinContent(
                    storage_bin,
                    float(values[storage_bin]),
                )
        else:
            # Only regular bins are stored.
            for storage_bin in range(n_stored):
                hist.AddBinContent(
                    storage_bin + 1,
                    float(values[storage_bin]),
                )

        if has_gen_sumw:
            total_gen_sumw += float(
                getattr(run_entry, "genEventSumw")
            )

    return hist, pu_cfg, total_gen_sumw, has_gen_sumw


def fill_events_pileup(root_file, pu_cfg, edges):
    events = root_file.Get("Events")

    if not events:
        raise RuntimeError("Could not find the Events tree")

    variable = pu_cfg.get(
        "variable",
        "Pileup_nTrueInt",
    )

    weight_branch = pu_cfg.get(
        "weight",
        "genWeight",
    )

    if not events.GetBranch(variable):
        raise RuntimeError(
            f"Events branch '{variable}' not found"
        )

    if not events.GetBranch(weight_branch):
        raise RuntimeError(
            f"Events branch '{weight_branch}' not found"
        )

    hist = make_hist(
        "pileup_from_events",
        "Pileup comparison;Pileup_nTrueInt;Weighted events",
        edges,
    )

    n_events = 0
    event_sumw = 0.0
    all_unit_weights = True

    for event in events:
        pu = float(
            getattr(event, variable)
        )

        weight = float(
            getattr(event, weight_branch)
        )

        hist.Fill(
            pu,
            weight,
        )

        n_events += 1
        event_sumw += weight

        if not math.isclose(
            weight,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            all_unit_weights = False

    print("\n=== Events tree ===")
    print(f"variable        : {variable}")
    print(f"weight          : {weight_branch}")
    print(f"Events entries  : {n_events}")
    print(f"sum(genWeight)  : {event_sumw}")
    print(f"all weights = 1 : {all_unit_weights}")

    return hist, event_sumw


def compare_histograms(h_runs, h_events, tolerance=1e-9):
    nbins = h_runs.GetNbinsX()

    max_abs_diff = 0.0
    max_rel_diff = 0.0
    n_mismatched = 0

    print("\n=== Bin-by-bin comparison ===")

    for root_bin in range(0, nbins + 2):
        a = h_runs.GetBinContent(root_bin)
        b = h_events.GetBinContent(root_bin)

        abs_diff = abs(a - b)

        scale = max(
            abs(a),
            abs(b),
            1.0,
        )

        rel_diff = abs_diff / scale

        max_abs_diff = max(
            max_abs_diff,
            abs_diff,
        )

        max_rel_diff = max(
            max_rel_diff,
            rel_diff,
        )

        if rel_diff > tolerance:
            n_mismatched += 1

            if root_bin == 0:
                label = "underflow"
            elif root_bin == nbins + 1:
                label = "overflow"
            else:
                low = h_runs.GetXaxis().GetBinLowEdge(
                    root_bin
                )
                high = h_runs.GetXaxis().GetBinUpEdge(
                    root_bin
                )
                label = f"[{low:g}, {high:g})"

            print(
                f"  bin {root_bin:3d} {label:>16s}: "
                f"Runs={a:.12g}, "
                f"Events={b:.12g}, "
                f"diff={a-b:+.6g}"
            )

    runs_integral = h_runs.Integral(
        0,
        nbins + 1,
    )

    events_integral = h_events.Integral(
        0,
        nbins + 1,
    )

    print(f"Runs integral   : {runs_integral:.12g}")
    print(f"Events integral : {events_integral:.12g}")
    print(f"max abs diff    : {max_abs_diff:.12g}")
    print(f"max rel diff    : {max_rel_diff:.12g}")
    print(f"mismatched bins : {n_mismatched}")

    return n_mismatched == 0


def make_plot(
    h_runs,
    h_events,
    output_name,
):
    ROOT.gStyle.SetOptStat(0)

    canvas = ROOT.TCanvas(
        "c",
        "Pileup bookkeeping validation",
        800,
        800,
    )

    upper = ROOT.TPad(
        "upper",
        "upper",
        0.0,
        0.30,
        1.0,
        1.0,
    )

    lower = ROOT.TPad(
        "lower",
        "lower",
        0.0,
        0.0,
        1.0,
        0.30,
    )

    upper.SetBottomMargin(0.02)
    lower.SetTopMargin(0.03)
    lower.SetBottomMargin(0.30)

    upper.Draw()
    lower.Draw()

    upper.cd()

    h_runs.SetLineWidth(2)
    h_events.SetLineWidth(2)
    h_events.SetLineStyle(2)

    maximum = max(
        h_runs.GetMaximum(),
        h_events.GetMaximum(),
    )

    h_runs.SetMaximum(
        1.20 * maximum
        if maximum > 0.0
        else 1.0
    )

    h_runs.GetXaxis().SetLabelSize(0.0)
    h_runs.Draw("HIST")
    h_events.Draw("HIST SAME")

    legend = ROOT.TLegend(
        0.58,
        0.72,
        0.88,
        0.88,
    )

    legend.SetBorderSize(0)
    legend.AddEntry(
        h_runs,
        "Runs bookkeeping",
        "l",
    )
    legend.AddEntry(
        h_events,
        "Events tree",
        "l",
    )
    legend.Draw()

    lower.cd()

    ratio = h_events.Clone(
        "pileup_events_over_runs"
    )

    ratio.SetDirectory(0)
    ratio.Divide(h_runs)

    ratio.SetTitle("")
    ratio.GetYaxis().SetTitle(
        "Events / Runs"
    )
    ratio.GetXaxis().SetTitle(
        "Pileup_nTrueInt"
    )

    ratio.GetYaxis().SetRangeUser(
        0.95,
        1.05,
    )

    ratio.GetYaxis().SetNdivisions(505)

    ratio.GetXaxis().SetTitleSize(0.11)
    ratio.GetXaxis().SetLabelSize(0.09)
    ratio.GetYaxis().SetTitleSize(0.10)
    ratio.GetYaxis().SetLabelSize(0.08)
    ratio.GetYaxis().SetTitleOffset(0.45)

    ratio.Draw("HIST")

    line = ROOT.TLine(
        h_runs.GetXaxis().GetXmin(),
        1.0,
        h_runs.GetXaxis().GetXmax(),
        1.0,
    )
    line.SetLineStyle(2)
    line.Draw()

    canvas.SaveAs(output_name)

    return ratio


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Validate Reco2Pico pileup bookkeeping by comparing "
            "Runs.pileupSumw with an independent histogram made "
            "from Events.Pileup_nTrueInt."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="../test_pico.root",
        help="Input Reco2Pico ROOT file",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="pileup_comparison.png",
        help="Output comparison plot",
    )

    parser.add_argument(
        "--root-output",
        default="pileup_comparison.root",
        help="ROOT file containing the reconstructed histograms",
    )

    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Relative tolerance for the bin-by-bin comparison",
    )

    args = parser.parse_args()

    root_file = ROOT.TFile.Open(
        args.input,
        "READ",
    )

    if not root_file or root_file.IsZombie():
        raise RuntimeError(
            f"Could not open input file '{args.input}'"
        )

    try:
        schema = get_schema(
            root_file
        )

        pu_cfg = schema["histograms"]["pileup"]

        edges = [ float(x) for x in pu_cfg["edges"] ]

        print("\n=== bookkeepingSchema ===")
        print(
            json.dumps(
                pu_cfg,
                indent=2,
                sort_keys=True,
            )
        )

        h_runs, pu_cfg, run_gen_sumw, has_gen_sumw = (
            read_runs_pileup(
                root_file,
                schema,
            )
        )

        h_events, event_sumw = (
            fill_events_pileup(
                root_file,
                pu_cfg,
                edges,
            )
        )

        if has_gen_sumw:
            print("\n=== genEventSumw consistency ===")
            print(
                f"Runs.genEventSumw : "
                f"{run_gen_sumw:.12g}"
            )
            print(
                f"Events sumw       : "
                f"{event_sumw:.12g}"
            )
            print(
                f"difference        : "
                f"{event_sumw-run_gen_sumw:+.12g}"
            )

        passed = compare_histograms(
            h_runs,
            h_events,
            tolerance=args.tolerance,
        )

        ratio = make_plot(
            h_runs,
            h_events,
            args.output,
        )

        output_file = ROOT.TFile.Open(
            args.root_output,
            "RECREATE",
        )

        h_runs.Write(
            "pileup_from_runs"
        )

        h_events.Write(
            "pileup_from_events"
        )

        ratio.Write(
            "pileup_events_over_runs"
        )

        output_file.Close()

        print("\n=== Result ===")
        print(
            "PASS: Runs bookkeeping matches Events."
            if passed
            else "FAIL: Runs bookkeeping does not match Events."
        )

        print(
            f"Saved plot: {args.output}"
        )

        print(
            f"Saved ROOT histograms: {args.root_output}"
        )

        if not passed:
            raise SystemExit(1)

    finally:
        root_file.Close()


if __name__ == "__main__":
    main()
