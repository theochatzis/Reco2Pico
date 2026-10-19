#!/usr/bin/env python3
"""
How much of each bunch crossing's deposit ends up in the in-time rechit, per subdetector,
on a classically mixed Pico with the per-crossing cell columns (SimCaloCell_ootBx*) and the
rechits group.

Two estimates of the weight w_bx such that  rechit ~ sum_bx w_bx * deposit_bx:
  * dominance: among the cells where one crossing carries more than DOM of all deposits,
    w_bx = sum(rechit) / sum(deposit_bx)  (robust, no correlation between crossings);
  * regression: non-negative least squares of the rechit on all crossings at once.
The in-time weight is the rechit scale of the sim deposit (RECHIT_SCALE in sim_cff.py); the
others are the leak of the pulse fit. Deposits are on the rechit GeV-equivalent scale as the
Pico writes them; cells without a rechit count with rechit = 0 (the threshold is part of the
answer, and the in-time weight is also given against the deposit and on the cells with a rechit
only, where the readout thresholds no longer bite).

usage: python3 measure_pulse_leak.py pico.root [pico2.root ...] [--min-deposit 0.1] [--dominance 0.8]
"""
import argparse

import numpy as np
import ROOT

BX = ["ootEarly", "ootBxm5", "ootBxm4", "ootBxm3", "ootBxm2", "ootBxm1", "inTime", "ootBxp1", "ootBxp2", "ootBxp3"]
SUBDETS = ["EB", "EE", "HB", "HE", "HF1", "HF2"]
RECHIT_TABLES = {"EB": "EBRecHit", "EE": "EERecHit", "HB": "HBHERecHit", "HE": "HBHERecHit", "HF1": "HFRecHit", "HF2": "HFRecHit"}


def subdet_of(raw):
    """the subdetector name from the raw DetId (EB EE HB HE HF1 HF2, else None)"""
    det = (raw >> 28) & 0xF
    sd = (raw >> 25) & 0x7
    if det == 3:
        return {1: "EB", 2: "EE"}.get(sd)
    if det == 4:
        depth = (raw >> 20) & 0xF if raw & 0x1000000 else (raw >> 14) & 0x7
        return {1: "HB", 2: "HE", 4: "HF1" if depth == 1 else "HF2"}.get(sd)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--min-deposit", type=float, default=0.1, help="largest single-crossing deposit of the cell [GeV-eq.]")
    ap.add_argument("--dominance", type=float, default=0.8, help="fraction of all deposits one crossing must carry")
    args = ap.parse_args()
    ROOT.ROOT.EnableImplicitMT()
    df = ROOT.RDataFrame("Events", args.inputs)
    cols = ["SimCaloCell_detId", "SimCaloCell_energy", "SimCaloCell_puEnergy"] + ["SimCaloCell_" + c for c in BX if c != "inTime"]
    rechit_cols = sorted({t for t in RECHIT_TABLES.values()})
    cols += [t + "_rawId" for t in rechit_cols] + [t + "_energy" for t in rechit_cols]
    a = df.AsNumpy(cols)
    nev = len(a["SimCaloCell_detId"])
    # per-event rechit lookup, then flat arrays
    rows = {s: [] for s in SUBDETS}
    sub_of = np.vectorize(lambda d: subdet_of(int(d)) or "", otypes=[object])
    for i in range(nev):
        rec = {}
        for t in rechit_cols:
            for r, e in zip(a[t + "_rawId"][i], a[t + "_energy"][i]):
                rec[int(r)] = e
        det = np.asarray(a["SimCaloCell_detId"][i])
        sub = sub_of(det) if len(det) else np.array([], dtype=object)
        dep = np.stack([np.asarray(a["SimCaloCell_" + c][i]) if c != "inTime" else np.asarray(a["SimCaloCell_energy"][i]) + np.asarray(a["SimCaloCell_puEnergy"][i]) for c in BX], axis=1)
        rh = np.array([rec.get(int(d), 0.0) for d in det])
        for name in SUBDETS:
            m = sub == name
            if m.any():
                rows[name].append((dep[m], rh[m]))
    print("events %d" % nev)
    from scipy.optimize import nnls
    for name, parts in rows.items():
        if not parts:
            continue
        dep = np.concatenate([p[0] for p in parts]); rh = np.concatenate([p[1] for p in parts])
        keep = dep.max(axis=1) > args.min_deposit
        dep, rh = dep[keep], rh[keep]
        if len(rh) < 20:
            print("%s: %d cells, too few" % (name, len(rh))); continue
        tot = dep.sum(axis=1)
        has = rh > 0
        w_nnls, _ = nnls(dep, rh)
        print("\n%s: %d cells with a crossing above %.2f GeV-eq., %.0f%% with a rechit" % (name, len(rh), args.min_deposit, 100.0 * has.mean()))
        print("  weight of each crossing in the rechit, from the cells it dominates (> %.0f%% of the deposits)" % (100 * args.dominance))
        print("  %-9s %8s %9s %14s %14s %10s" % ("crossing", "cells", "rechit", "w (all cells)", "w (with rechit)", "nnls"))
        for j, c in enumerate(BX):
            m = dep[:, j] > args.dominance * tot
            w_all = rh[m].sum() / dep[m, j].sum() if m.sum() >= 5 else float("nan")
            w_has = rh[m & has].sum() / dep[m & has, j].sum() if (m & has).sum() >= 5 else float("nan")
            print("  %-9s %8d %8.0f%% %14.3f %14.3f %10.3f" % (c, m.sum(), 100.0 * has[m].mean() if m.any() else 0.0, w_all, w_has, w_nnls[j]))
        # the in-time weight against the deposit: where the readout threshold bites
        j = BX.index("inTime")
        m = dep[:, j] > args.dominance * tot
        print("  in-time dominated cells by deposit: cells, with a rechit, rechit/deposit (all, with rechit)")
        for lo, hi in [(0.1, 0.3), (0.3, 0.6), (0.6, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 20.0), (20.0, 1e9)]:
            b = m & (dep[:, j] >= lo) & (dep[:, j] < hi)
            if b.sum() >= 3:
                print("    %5.1f-%5.1f %6d %5.0f%% %6.2f %6.2f" % (lo, min(hi, 999), b.sum(), 100.0 * has[b].mean(), rh[b].sum() / dep[b, j].sum(),
                                                               (rh[b & has].sum() / dep[b & has, j].sum()) if (b & has).any() else float("nan")))


if __name__ == "__main__":
    main()
