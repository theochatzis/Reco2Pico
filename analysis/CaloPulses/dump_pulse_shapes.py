#!/usr/bin/env python3
"""
Write pulse_shapes.json: the pulse templates the reconstruction and the simulation use,
sampled every nanosecond, for the cell figures of plot_cell_pulse.py.

  HB, HE   the HCAL SiPM shape of the reconstruction (HcalPulseShapes, id from the
           HcalRecoParams of the global tag: 208, the Run-3 MC shape), normalised to
           unit integral as CMSSW keeps it;
  EB, EE   the ECAL simulation pulse (EcalSimPulseShape payload of the global tag, 1 ns
           steps, peak-normalised), read from a `conddb dump` of the payload.

usage (cmsenv): python3 dump_pulse_shapes.py [--hcal-shape 208] [--ecal-tag EcalSimPulseShapePhaseI]
"""
import argparse
import json
import os
import re
import subprocess

import ROOT

HERE = os.path.dirname(os.path.abspath(__file__))


def hcal_shape(shape_id):
    ROOT.gSystem.Load("libCalibCalorimetryHcalAlgos")
    ROOT.gErrorIgnoreLevel = ROOT.kError
    ROOT.gInterpreter.Declare('#include "CalibCalorimetry/HcalAlgos/interface/HcalPulseShapes.h"')
    sh = ROOT.HcalPulseShapes().getShape(shape_id)
    return [sh.at(t) for t in range(sh.nbins())]


def ecal_shapes(tag):
    out = subprocess.run(["conddb", "--db", "pro", "list", tag], capture_output=True, text=True).stdout
    payload = [l.split()[-2] for l in out.splitlines() if "EcalSimPulseShape" in l][-1]
    xml = subprocess.run(["conddb", "--db", "pro", "dump", payload], capture_output=True, text=True).stdout
    shapes = {}
    for key, name in (("barrel-shape", "EB"), ("endcap-shape", "EE")):
        block = re.search("<%s>(.*?)</%s>" % (key, key), xml, re.S).group(1)
        vals = [float(v) for v in re.findall(r"<item>([^<]+)</item>", block)]
        peak = max(vals)
        shapes[name] = [v / peak for v in vals]
    dt = float(re.search(r"<time-interval>([^<]+)</time-interval>", xml).group(1))
    return shapes, dt, payload


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hcal-shape", type=int, default=208)
    ap.add_argument("--ecal-tag", default="EcalSimPulseShapePhaseI")
    ap.add_argument("--output", default=os.path.join(HERE, "pulse_shapes.json"))
    args = ap.parse_args()
    h = hcal_shape(args.hcal_shape)
    e, dt, payload = ecal_shapes(args.ecal_tag)
    out = {
        "note": "pulse templates sampled every nanosecond; HCAL unit integral, ECAL peak 1",
        "HB": {"source": "HcalPulseShapes id %d" % args.hcal_shape, "dt_ns": 1.0, "values": h},
        "HE": {"source": "HcalPulseShapes id %d" % args.hcal_shape, "dt_ns": 1.0, "values": h},
        "EB": {"source": "%s (%s) barrel" % (args.ecal_tag, payload), "dt_ns": dt, "values": e["EB"]},
        "EE": {"source": "%s (%s) endcap" % (args.ecal_tag, payload), "dt_ns": dt, "values": e["EE"]},
    }
    with open(args.output, "w") as f:
        json.dump(out, f)
    for k in ("HB", "EB", "EE"):
        v = out[k]["values"]
        print("%s: %d points, peak at %d ns" % (k, len(v), v.index(max(v))))


if __name__ == "__main__":
    main()
