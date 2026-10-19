#!/usr/bin/env python3
"""
One calorimeter cell of a classically mixed event, from the deposits to the rechit: the
matching cases the per-cell attribution has to handle (needs a Pico with pileupTruth and
the rechits group).

  cells_matching_cases/<case>_<sub>_<event>   two panels for one cell:
      left   the simulated deposits per bunch crossing (signal and in-time pile-up at 0,
             the out-of-time interactions at -5..+3 and the sum of the earlier ones) and,
             next to them, the rechit split by the attribution into signal, pile-up and
             the residual;
      right  the pulse shapes: the detector's template (pulse_shapes.json from
             dump_pulse_shapes.py: the HCAL reconstruction shape, the ECAL simulation
             pulse) once per crossing scaled to that crossing's deposit and shifted by
             25 ns each, their sum, and the samples: the digis of the cell when the Pico
             has the calodigis group (EBDigi/HBHEDigi, pedestal subtracted, on the
             rechit scale), otherwise the sum of the templates at the sample times.
             ECAL: the amplitude is the peak (multifit), so peak = deposit and the
             samples are instantaneous values. HCAL: the amplitude is the integrated
             charge (MAHI), so the template has unit integral, the curve is drawn per
             25 ns and each sample is the integral over its 25 ns window.

The cases, chosen per event and subdetector among the cells with a rechit:
  signal_only      the largest signal deposit with no in-time pile-up in the cell
  signal_pileup    the most energetic cell where signal and in-time pile-up both exceed 0.1 GeV
  pileup_only      the largest in-time pile-up deposit with no signal in the cell
  out_of_time      the cell with the largest out-of-time deposit relative to its in-time one
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "SkimRDFAnalysisBase"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import ROOT  # noqa: E402
from plotting.plotters import save_figure, draw_cms_label, use_hep_style  # noqa: E402

# the rechit scale of the sim deposits per subdetector, as in the Pico producer
RECHIT_SCALE = {"EB": 1.0, "EE": 1.05, "ES": 1.0, "HB": 0.74, "HE": 0.75, "HO": 1.05, "HF1": 14.2, "HF2": 12.8}
COL_SIG, COL_PU, COL_OOT, COL_RES, COL_REC = "#5790fc", "#7a21dd", "#9c9ca1", "#f0f0f0", "#e42536"
BX = list(range(-5, 4))
BX_COLS = {-5: "ootBxm5", -4: "ootBxm4", -3: "ootBxm3", -2: "ootBxm2", -1: "ootBxm1", 1: "ootBxp1", 2: "ootBxp2", 3: "ootBxp3"}
CASES = {
    "signal_only": "signal only: the cell of a signal particle, no pile-up in it",
    "signal_pileup": "signal and pile-up in the same cell: shared in proportion to the deposits",
    "pileup_only": "pile-up only: no signal, nothing to attribute to the jet",
    "out_of_time": "out-of-time dominated: what the pulse fit has to take out",
}
# ECAL: 10 samples, the in-time peak at the sixth (time axis: ns from the in-time peak).
# HCAL: 8 samples of 25 ns, the in-time pulse starting at the sample of interest (time axis:
# ns from the start of the in-time pulse; the digi's soi says which sample that is, 3 by default).
NSAMPLES = {"EB": 10, "EE": 10, "HB": 8, "HE": 8}  # HCAL: overridden by the digi's nSamples when present
ECAL = {"EB", "EE"}
DIGI_TABLE = {"EB": "EBDigi", "EE": "EEDigi", "HB": "HBHEDigi", "HE": "HBHEDigi"}
SHAPE_LABEL = {"EB": "ECAL simulation pulse, peak = deposit", "EE": "ECAL simulation pulse, peak = deposit",
               "HB": "HCAL template 208, integral = deposit", "HE": "HCAL template 208, integral = deposit"}
_SHAPES = None


def template(sub):
    """(t [ns], value per ns) of the template: ECAL peak 1 at t = 0; HCAL unit integral, start at t = 0"""
    global _SHAPES
    if _SHAPES is None:
        with open(os.path.join(HERE, "pulse_shapes.json")) as f:
            raw = json.load(f)
        _SHAPES = {}
        for k, v in raw.items():
            if isinstance(v, dict) and "values" in v:
                vals = np.array(v["values"], dtype=float)
                tt = v["dt_ns"] * np.arange(len(vals))
                if k in ECAL:
                    vals = vals / vals.max()
                    tt = tt - tt[int(np.argmax(vals))]
                else:
                    vals = vals / (vals.sum() * v["dt_ns"])
                    first = int(np.argmax(vals > 1e-4 * vals.max()))
                    tt = tt - tt[first]
                _SHAPES[k] = (tt, vals)
    return _SHAPES[sub]


def pulse(sub, t_ns):
    """the template at t_ns: ECAL the amplitude (peak 1), HCAL the charge per 25 ns (integral 25 ns ... 1 x 25)"""
    tt, vals = template(sub)
    out = np.interp(t_ns, tt, vals, left=0.0, right=0.0)
    return out if sub in ECAL else 25.0 * out


def sample_times(sub, soi=3, n=None):
    """the times of the digitiser samples on the axis of the figure"""
    n = n or NSAMPLES[sub]
    if sub in ECAL:
        return np.array([25.0 * (i - 5) for i in range(n)])
    return np.array([25.0 * (i - soi) + 12.5 for i in range(n)])


def predicted_samples(sub, tt, total, soi=3, n=None):
    """what the summed templates give at the samples: ECAL the value, HCAL the integral of the 25 ns window"""
    times = sample_times(sub, soi, n)
    if sub in ECAL:
        return times, np.interp(times, tt, total)
    out = []
    for t0 in times - 12.5:
        m = (tt >= t0) & (tt < t0 + 25.0)
        out.append(np.trapz(total[m] / 25.0, tt[m]) if m.sum() > 1 else 0.0)
    return times, np.array(out)


def digi_samples(t, sub, raw):
    """(times, values, soi) of the cell's digi in the Pico, or None"""
    tab = DIGI_TABLE[sub]
    if not hasattr(t, "n" + tab):
        return None
    ids = getattr(t, tab + "_rawId")
    for k in range(getattr(t, "n" + tab)):
        if int(ids[k]) == raw:
            soi = getattr(t, tab + "_soi")[k] if sub not in ECAL else 5
            n = getattr(t, tab + "_nSamples")[k] if sub not in ECAL else NSAMPLES[sub]
            vals = np.array([getattr(t, "%s_e%d" % (tab, i))[k] for i in range(n)])
            return sample_times(sub, soi, n), vals, soi, n
    return None


def subdet_of(raw):
    det = (raw >> 28) & 0xF
    sd = (raw >> 25) & 0x7
    if det == 3:
        return {1: "EB", 2: "EE", 6: "ES"}.get(sd)
    if det == 4:
        depth = (raw >> 20) & 0xF if raw & 0x1000000 else (raw >> 14) & 0x7
        return {1: "HB", 2: "HE", 3: "HO", 4: "HF1" if depth == 1 else "HF2"}.get(sd)
    return None


def cell_figure(t, i, k, sub, case, rechit, output, raw=None):
    use_hep_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    sig, pu = t.SimCaloCell_energy[k], t.SimCaloCell_puEnergy[k]
    oot = {bx: getattr(t, "SimCaloCell_" + c)[k] for bx, c in BX_COLS.items()}
    early = t.SimCaloCell_ootEarly[k]
    scale = RECHIT_SCALE[sub]
    npu = t.SimCaloCell_nPU[k]
    ntrue = t.Pileup_nTrueInt if hasattr(t, "Pileup_nTrueInt") else -1

    # ---- left: deposits per crossing, and the rechit attributed
    ax = axes[0]
    ax.bar([-6.5], [early], width=0.8, color=COL_OOT)
    ax.bar([bx for bx in BX if bx != 0], [oot[bx] for bx in BX if bx != 0], width=0.8, color=COL_OOT, label="out-of-time pile-up")
    ax.bar([0], [sig], width=0.8, color=COL_SIG, label="signal")
    ax.bar([0], [pu], width=0.8, bottom=[sig], color=COL_PU, label="in-time pile-up")
    cap = scale * (sig + pu)
    attributed = min(rechit, cap) if rechit > 0 else 0.0
    s_share = attributed * sig / (sig + pu) if sig + pu > 0 else 0.0
    p_share = attributed - s_share
    residual = max(0.0, rechit - attributed)
    xr = 5.6
    ax.bar([xr], [s_share], width=0.8, color=COL_SIG)
    ax.bar([xr], [p_share], width=0.8, bottom=[s_share], color=COL_PU)
    ax.bar([xr], [residual], width=0.8, bottom=[attributed], color=COL_RES, edgecolor="#555555", hatch="//", label="residual: noise, out-of-time, calibration")
    ax.plot([xr - 0.5, xr + 0.5], [rechit, rechit], color=COL_REC, linewidth=2.5, label="rechit")
    ax.axvline(4.6, color="gray", linewidth=0.8, linestyle=":")
    ax.set_xticks([-6.5] + BX + [xr])
    ax.set_xticklabels(["< -5"] + [str(b) for b in BX] + ["rechit"])
    ax.set_xlabel("bunch crossing")
    ax.set_ylabel("GeV-equivalent")
    ax.set_ylim(0, 2.3 * max(sig + pu, max(oot.values()), early, rechit, 1e-3))
    ax.legend(fontsize="x-small", loc="upper left", frameon=False)
    ax.text(0.97, 0.96, "rechit %.2f GeV\nsignal %.0f%%\npile-up %.0f%%\nresidual %.0f%%" % ((rechit,) + tuple(100 * max(v, 0.0) / max(rechit, 1e-9) for v in (s_share, p_share, residual))),
            transform=ax.transAxes, ha="right", va="top", fontsize="x-small")

    # ---- right: the pulse shapes
    ax = axes[1]
    tt = np.linspace(-200, 200, 1601)
    total = np.zeros_like(tt)
    first = True
    digi = digi_samples(t, sub, raw) if raw is not None else None
    soi = digi[2] if digi else 3
    nsam = digi[3] if digi else None
    for bx in BX + [-6]:
        e = (sig + pu) if bx == 0 else (early if bx == -6 else oot[bx])
        if e <= 0:
            continue
        w = e * pulse(sub, tt - 25.0 * bx)
        total += w
        if bx == 0:
            ax.plot(tt, w, color=COL_SIG, linewidth=2.0, label="in-time pulse")
        else:
            ax.plot(tt, w, color=COL_OOT, linewidth=1.0, label="out-of-time pulses" if first else None)
            first = False
    ax.plot(tt, total, color="black", linewidth=2.2, label="sum")
    times, pred = predicted_samples(sub, tt, total, soi, nsam)
    if digi:
        ax.plot(digi[0], digi[1], "o-", color=COL_REC, markersize=7, linewidth=1.0, label="digi samples (pedestal subtracted)")
        ax.plot(times, pred, "o", markerfacecolor="none", markeredgecolor="black", markersize=7, label="templates at the samples")
    else:
        ax.plot(times, pred, "o", color=COL_REC, markersize=7, label="templates at the sample times (no digis in the Pico)")
    ax.set_xticks([25.0 * b for b in range(-6, 7, 2)])
    ax.set_xticklabels([str(b) for b in range(-6, 7, 2)])
    ax.set_xlabel("bunch crossing (25 ns)")
    ymax = max(total.max(), pred.max(), (digi[1].max() if digi else 0.0), 1e-3)
    ax.set_ylim(min(0.0, (digi[1].min() if digi else 0.0)) * 1.2, 2.1 * ymax)
    ax.set_ylabel("amplitude [GeV-equivalent]" if sub in ECAL else "charge / 25 ns [GeV-equivalent]")
    ax.legend(fontsize="x-small", loc="upper left", frameon=False, title=SHAPE_LABEL[sub], title_fontsize="x-small")

    draw_cms_label(axes[0], cms_label="", data=False, com=13.6)
    fig.suptitle("%s\n%s cell, $\\eta$ = %.2f, $\\phi$ = %.2f, event %d with %.0f in-time interactions, %d of them in this cell"
                 % (CASES[case], sub, t.SimCaloCell_eta[k], t.SimCaloCell_phi[k], i, ntrue, npu), fontsize="small", y=0.995)
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.14, top=0.84, wspace=0.22)
    save_figure(fig, output)
    plt.close(fig)


def pick_cases(t, sub, rechits):
    """the example cells of one subdetector: {case: row}"""
    rows = [k for k in range(t.nSimCaloCell) if subdet_of(int(t.SimCaloCell_detId[k])) == sub and int(t.SimCaloCell_detId[k]) in rechits]
    if not rows:
        return {}
    e = np.array([t.SimCaloCell_energy[k] for k in rows])
    p = np.array([t.SimCaloCell_puEnergy[k] for k in rows])
    o = np.array([t.SimCaloCell_ootEnergy[k] for k in rows])

    def best(mask, score):
        idx = np.where(mask)[0]
        return rows[idx[np.argmax(score[idx])]] if idx.size else None

    out = {
        "signal_only": best((p < 0.02) & (e > 0.1), e),
        "signal_pileup": best((e > 0.1) & (p > 0.1), e + p),
        "pileup_only": best((e < 0.02) & (p > 0.1), p),
        "out_of_time": best((e + p > 0.1) & (o > 0.5), o / (e + p + 1e-9)),
    }
    return {k: v for k, v in out.items() if v is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Pico with pileupTruth and the rechits group")
    parser.add_argument("--output-dir", default="plots")
    parser.add_argument("--subdets", nargs="*", default=["EB", "HB"])
    parser.add_argument("--events", type=int, default=2, help="number of events (one figure per case and subdetector each)")
    args = parser.parse_args()
    outdir = os.path.join(args.output_dir, "cells_matching_cases")
    os.makedirs(outdir, exist_ok=True)
    f = ROOT.TFile.Open(args.input)
    t = f.Get("Events")
    done = 0
    for i in range(t.GetEntries()):
        t.GetEntry(i)
        if t.nSimCaloCell == 0:
            continue
        rechits = {}
        for tab in ("EBRecHit", "EERecHit", "HBHERecHit"):
            if hasattr(t, "n" + tab):
                for r, e in zip(getattr(t, tab + "_rawId"), getattr(t, tab + "_energy")):
                    rechits[int(r)] = e
        for sub in args.subdets:
            for case, k in pick_cases(t, sub, rechits).items():
                raw = int(t.SimCaloCell_detId[k])
                out = [os.path.join(outdir, "%s_%s_%d.%s" % (case, sub, i, ext)) for ext in ("pdf", "png")]
                cell_figure(t, i, k, sub, case, rechits[raw], out, raw)
                print("event %d %s %-14s signal %.2f pile-up %.2f out-of-time %.2f rechit %.2f -> %s" % (
                    i, sub, case, t.SimCaloCell_energy[k], t.SimCaloCell_puEnergy[k], t.SimCaloCell_ootEnergy[k], rechits[raw], out[1]))
        done += 1
        if done >= args.events:
            break


if __name__ == "__main__":
    main()
