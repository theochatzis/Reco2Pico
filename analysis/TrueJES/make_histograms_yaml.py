#!/usr/bin/env python3
"""Write truejes_histograms.yaml from the levels, eta regions and pt bins of
truejes_rdf_definition.py (one TProfile of the response vs gen pt, one
TProfile of the match efficiency vs gen pt, one TH2 and the response
distributions per gen-pt bin, for every level and eta region)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truejes_rdf_definition import ALL_LEVELS as LEVELS, ETA_EDGES, ETA_REGIONS, GEN_TYPES, OFFSET_COLLECTIONS, OFFSET_TYPES, PT_BINS, PT_EDGES, SHARED_LEVELS, SIMPF_KINDS, pt_bin_label  # noqa: E402

out = []
edges = ", ".join(str(e) for e in PT_EDGES)
for region in ETA_REGIONS:
    out.append(
        "GenPt_%s:\n  type: TH1D\n  title: \"gen jet p_{T} (%s);p_{T}^{GEN} [GeV];Jets\"\n  edges: [%s]\n  variable: GenPt_%s\n  weight: null\n"
        % (region, region, edges, region)
    )
    for level in SHARED_LEVELS:
        out.append(
            "RespShared_%s_%s:\n  type: TProfile\n  title: \"<E_{shared}/E^{GEN}> %s (%s);p_{T}^{GEN} [GeV];<E_{shared}/E^{GEN}>\"\n  edges: [%s]\n  variable_x: GenPtS_%s_%s\n  variable_y: Sm_%s_%s\n  weight: null\n"
            % (level, region, level, region, edges, level, region, level, region)
        )
    for level in LEVELS:
        out.append(
            "Resp_%s_%s:\n  type: TProfile\n  title: \"<p_{T}/p_{T}^{GEN}> %s (%s);p_{T}^{GEN} [GeV];<p_{T}/p_{T}^{GEN}>\"\n  edges: [%s]\n  variable_x: GenPtm_%s_%s\n  variable_y: Rm_%s_%s\n  weight: null\n"
            % (level, region, level, region, edges, level, region, level, region)
        )
        out.append(
            "Eff_%s_%s:\n  type: TProfile\n  title: \"match efficiency %s (%s);p_{T}^{GEN} [GeV];matched fraction\"\n  edges: [%s]\n  variable_x: GenPt_%s\n  variable_y: M_%s_%s\n  weight: null\n"
            % (level, region, level, region, edges, region, level, region)
        )
        out.append(
            "Resp2D_%s_%s:\n  type: TH2D\n  title: \"p_{T}/p_{T}^{GEN} vs p_{T}^{GEN} %s (%s);p_{T}^{GEN} [GeV];p_{T}/p_{T}^{GEN}\"\n  edges_x: [%s]\n  edges_y: [\"bins\", 60, 0, 3]\n  variable_x: GenPtm_%s_%s\n  variable_y: Rm_%s_%s\n  weight: null\n"
            % (level, region, level, region, edges, level, region, level, region)
        )
        for lo, hi in PT_BINS:
            lab = pt_bin_label(lo, hi)
            out.append(
                "RespDist_%s_%s_%s:\n  type: TH1D\n  title: \"p_{T}/p_{T}^{GEN} %s (%s, %d < p_{T}^{GEN} < %d GeV);p_{T}/p_{T}^{GEN};Jets\"\n  bins: [60, 0, 3]\n  variable: Rm_%s_%s_%s\n  weight: null\n"
                % (level, region, lab, level, region, lo, hi, level, region, lab)
            )
eta_edges = ", ".join(str(e) for e in ETA_EDGES)
for coll in OFFSET_COLLECTIONS:
    for typ in OFFSET_TYPES:
        for region in ETA_REGIONS:
            out.append(
                "Offset_%s_%s_%s:\n  type: TProfile\n  title: \"offset %s %s (%s);p_{T}^{GEN} [GeV];<p_{T}^{offset}> [GeV]\"\n  edges: [%s]\n  variable_x: GenPtO_%s_%s\n  variable_y: Om_%s_%s_%s\n  weight: null\n"
                % (coll, typ, region, coll, typ, region, edges, coll, region, coll, typ, region)
            )
        for lo, hi in PT_BINS:
            lab = pt_bin_label(lo, hi)
            out.append(
                "OffsetEta_%s_%s_%s:\n  type: TProfile\n  title: \"offset %s %s (%d < p_{T}^{GEN} < %d GeV);|#eta^{GEN}|;<p_{T}^{offset}> [GeV]\"\n  edges: [%s]\n  variable_x: GenAbsEtaO_%s_%s\n  variable_y: Oe_%s_%s_%s\n  weight: null\n"
                % (coll, typ, lab, coll, typ, lo, hi, eta_edges, coll, lab, coll, typ, lab)
            )
        # the true in-time pile-up part and the residual of the offset (pile-up truth; empty otherwise)
        for name, var in (("OffsetPU", "OPU"), ("OffsetRes", "ORES")):
            for region in ETA_REGIONS:
                out.append(
                    "%s_%s_%s_%s:\n  type: TProfile\n  title: \"%s %s %s (%s);p_{T}^{GEN} [GeV];<p_{T}> [GeV]\"\n  edges: [%s]\n  variable_x: GenPtO_%s_%s\n  variable_y: %sm_%s_%s_%s\n  weight: null\n"
                    % (name, coll, typ, region, name, coll, typ, region, edges, coll, region, var, coll, typ, region)
                )
            for lo, hi in PT_BINS:
                lab = pt_bin_label(lo, hi)
                out.append(
                    "%sEta_%s_%s_%s:\n  type: TProfile\n  title: \"%s %s %s (%d < p_{T}^{GEN} < %d GeV);|#eta^{GEN}|;<p_{T}> [GeV]\"\n  edges: [%s]\n  variable_x: GenAbsEtaO_%s_%s\n  variable_y: %se_%s_%s_%s\n  weight: null\n"
                    % (name, coll, typ, lab, name, coll, typ, lo, hi, eta_edges, coll, lab, var, coll, typ, lab)
                )
# composition by flavour: fraction of the gen pt carried by each component at the generator, in the
# ideal PF (by kind) and in the signal part of the reconstructed jets (by candidate type)
for region in ETA_REGIONS:
    for typ in GEN_TYPES:
        out.append(
            "GenComp_%s_%s:\n  type: TProfile\n  title: \"gen jet composition %s (%s);p_{T}^{GEN} [GeV];fraction of p_{T}^{GEN}\"\n  edges: [%s]\n  variable_x: GenPt_%s\n  variable_y: GTm_%s_%s\n  weight: null\n"
            % (typ, region, typ, region, edges, region, typ, region)
        )
    for kind in SIMPF_KINDS:
        out.append(
            "SimPFComp_%s_%s:\n  type: TProfile\n  title: \"ideal PF composition %s (%s);p_{T}^{GEN} [GeV];fraction of p_{T}^{GEN}\"\n  edges: [%s]\n  variable_x: GenPtK_%s\n  variable_y: SKm_%s_%s\n  weight: null\n"
            % (kind, region, kind, region, edges, region, kind, region)
        )
    for coll in OFFSET_COLLECTIONS:
        for typ in OFFSET_TYPES:
            out.append(
                "SigComp_%s_%s_%s:\n  type: TProfile\n  title: \"signal part by type %s %s (%s);p_{T}^{GEN} [GeV];fraction of p_{T}^{GEN}\"\n  edges: [%s]\n  variable_x: GenPtO_%s_%s\n  variable_y: SGm_%s_%s_%s\n  weight: null\n"
                % (coll, typ, region, coll, typ, region, edges, coll, region, coll, typ, region)
            )
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truejes_histograms.yaml")
open(path, "w").write("# generated by make_histograms_yaml.py, do not edit\n" + "\n".join(out))
print("wrote %s (%d histograms)" % (path, len(out)))
