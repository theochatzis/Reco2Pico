"""
TrueJES: jet energy scale decomposed along the truth ladder.

RDF definition for SkimRDFAnalysisBase/run_analysis.py on the Reco2Pico
run3_rawsim Picos (groups genparts, sim, simcalo, recojets).

For every GenJet (anti-kt 0.4, no neutrinos, re-clustered in the Pico job) the
response pT/pT_GEN is taken at every step of the ladder from the ancestry
match tables, with the pair that is best for the gen jet and passes the two
fraction requirements (analysis config: min_gen_fraction, min_other_fraction):

    Sim      SimJet       decays in flight and conversions (Geant4 particle list)
    SimCalo  SimCaloJet   the calorimeter response (per-particle sim deposits)
    SimPF    SimPFJet     ideal particle flow (perfect tracking + deposits)
    PF       PFJet        reconstructed, raw, all pile-up           [PFSig: signal part only]
    CHS      PFJetCHS     reconstructed, raw, charged-hadron subtraction [CHSSig]
    Puppi    PFJetPuppi   reconstructed, raw, Puppi                 [PuppiSig]

S_<level> is the shared-energy response sharedEnergy / E_GEN: only the energy of
the matched jet that descends from the gen jet. It is immune to the foreign
energy (underlying event, neighbouring jets) that a matched jet picks up, which
pushes the plain pT ratio above one at low pT.

The *Sig variants use signalPtRatio: the pt of the constituents attributed to
signal particles over the gen pt, i.e. the response with the pile-up removed
by attribution. For them and for S_<level> the purity requirement is not
applied (only genFraction and the best-pair flag), since a pile-up dominated
jet still measures the gen jet's own energy correctly. Gen jets within lepton_veto_dr of a generator muon above
lepton_min_pt (the Z decay) are excluded.

Columns are RVecs aligned with GenJet; the eta regions and gen-pt bins are
applied as masks when the histogram columns are defined, so one region
("all") is enough for the driver.
"""
import ROOT


LEVELS = {
    # name: (match table, "other" fraction column, ratio column)
    "Sim":      ("SimGenJetMatch",     "simFraction",  "ptRatio"),
    "SimCalo":  ("SimCaloGenJetMatch", "simFraction",  "ptRatio"),
    "SimPF":    ("SimPFGenJetMatch",   "simFraction",  "ptRatio"),
    "PF":       ("PFJetGenMatch",      "recoFraction", "ptRatio"),
    "PFSig":    ("PFJetGenMatch",      "recoFraction", "signalPtRatio"),
    "CHS":      ("PFJetCHSGenMatch",   "recoFraction", "ptRatio"),
    "CHSSig":   ("PFJetCHSGenMatch",   "recoFraction", "signalPtRatio"),
    "Puppi":    ("PFJetPuppiGenMatch", "recoFraction", "ptRatio"),
    "PuppiSig": ("PFJetPuppiGenMatch", "recoFraction", "signalPtRatio"),
}
ALL_LEVELS = list(LEVELS) + ["PuppiCorr", "PuppiSigCorr"]

# JEC-corrected Puppi levels: ratio of the level above times a per-jet factor
# (GlobalTag AK4PFPuppi corrections stored in the Pico as PFJetPuppi_jecL1,
# PFJetPuppi_jecL1L2L3). The raw jet gets the full L1FastL2L3 factor; the
# signal part has no pile-up to subtract and gets the L2L3 part only.
CORRECTED_LEVELS = {
    # name: (base level, factor expression per PFJetPuppi row)
    "PuppiCorr":    ("Puppi",    "PFJetPuppi_jecL1L2L3"),
    "PuppiSigCorr": ("PuppiSig", "PFJetPuppi_jecL1L2L3 / PFJetPuppi_jecL1"),
}

# levels with a shared-energy response (sharedEnergy / E_gen: only the energy
# descending from the gen jet; for the reco levels this is signal-from-g only)
SHARED_LEVELS = ["Sim", "SimCalo", "SimPF", "PF", "CHS", "Puppi"]

ETA_REGIONS = {
    "Incl": (0.0, 5.0),
    "HB":   (0.0, 1.3),
    "HE1":  (1.3, 2.5),
    "HE2":  (2.5, 3.0),
    "HF":   (3.0, 5.0),
}

# gen-pt bins of the response distributions (low pt is the focus)
PT_BINS = [(5, 8), (8, 13), (13, 20), (20, 30), (30, 50), (50, 100), (100, 300)]

# TProfile / TH2 edges of the response vs gen pt
PT_EDGES = [5, 6.5, 8, 10, 13, 16, 20, 25, 30, 40, 50, 70, 100, 150, 300]


def pt_bin_label(lo, hi):
    return "pt%dto%d" % (lo, hi)


CPP_HELPERS = r"""
#include "ROOT/RVec.hxx"
#include <cmath>
using ROOT::VecOps::RVec;

// response of every gen jet at one level: the pair flagged best for the gen jet,
// if both fractions pass; -1 otherwise
RVec<float> truejesBestRatio(const RVec<float>& genPt,
                             const RVec<int>& genIdx,
                             const RVec<unsigned char>& bestForGen,
                             const RVec<float>& genFrac,
                             const RVec<float>& otherFrac,
                             const RVec<float>& ratio,
                             float minGenFrac, float minOtherFrac) {
  RVec<float> out(genPt.size(), -1.f);
  for (size_t i = 0; i < genIdx.size(); ++i) {
    const int g = genIdx[i];
    if (g < 0 || size_t(g) >= out.size() || !bestForGen[i]) continue;
    if (genFrac[i] < minGenFrac || otherFrac[i] < minOtherFrac) continue;
    out[g] = ratio[i];
  }
  return out;
}

// shared-energy response of every gen jet at one level: sharedEnergy / E(gen jet)
// for the pair flagged best for the gen jet (same fraction requirements); -1 otherwise.
// Counts only the energy that descends from the gen jet, so foreign energy
// clustered into the matched jet (underlying event, neighbours) does not enter.
RVec<float> truejesBestShared(const RVec<float>& genPt, const RVec<float>& genEta, const RVec<float>& genMass,
                              const RVec<int>& genIdx,
                              const RVec<unsigned char>& bestForGen,
                              const RVec<float>& genFrac,
                              const RVec<float>& otherFrac,
                              const RVec<float>& shared,
                              float minGenFrac, float minOtherFrac) {
  RVec<float> out(genPt.size(), -1.f);
  for (size_t i = 0; i < genIdx.size(); ++i) {
    const int g = genIdx[i];
    if (g < 0 || size_t(g) >= out.size() || !bestForGen[i]) continue;
    if (genFrac[i] < minGenFrac || otherFrac[i] < minOtherFrac) continue;
    const float p = genPt[g] * std::cosh(genEta[g]);
    const float e = std::sqrt(p * p + genMass[g] * genMass[g]);
    out[g] = e > 0 ? shared[i] / e : -1.f;
  }
  return out;
}

// response scaled by a per-jet factor (JEC): same selection as truejesBestRatio
RVec<float> truejesBestRatioScaled(const RVec<float>& genPt,
                                   const RVec<int>& genIdx,
                                   const RVec<int>& jetIdx,
                                   const RVec<unsigned char>& bestForGen,
                                   const RVec<float>& genFrac,
                                   const RVec<float>& otherFrac,
                                   const RVec<float>& ratio,
                                   const RVec<float>& factor,
                                   float minGenFrac, float minOtherFrac) {
  RVec<float> out(genPt.size(), -1.f);
  for (size_t i = 0; i < genIdx.size(); ++i) {
    const int g = genIdx[i], j = jetIdx[i];
    if (g < 0 || size_t(g) >= out.size() || !bestForGen[i]) continue;
    if (j < 0 || size_t(j) >= factor.size()) continue;
    if (genFrac[i] < minGenFrac || otherFrac[i] < minOtherFrac) continue;
    out[g] = ratio[i] * factor[j];
  }
  return out;
}

// 1 where the response is defined (matched), 0 otherwise
RVec<float> truejesMatchedFlag(const RVec<float>& r) {
  RVec<float> out(r.size(), 0.f);
  for (size_t i = 0; i < r.size(); ++i) out[i] = r[i] > 0 ? 1.f : 0.f;
  return out;
}

// 1 for gen jets within dR of any of the given directions
RVec<int> truejesNearAny(const RVec<float>& eta, const RVec<float>& phi,
                         const RVec<float>& refEta, const RVec<float>& refPhi, float dr) {
  RVec<int> out(eta.size(), 0);
  for (size_t i = 0; i < eta.size(); ++i)
    for (size_t j = 0; j < refEta.size(); ++j) {
      float dphi = std::fabs(phi[i] - refPhi[j]);
      if (dphi > M_PI) dphi = 2 * M_PI - dphi;
      if (std::hypot(eta[i] - refEta[j], dphi) < dr) { out[i] = 1; break; }
    }
  return out;
}
"""


def setup(args=None, config=None):
    ROOT.gInterpreter.Declare(CPP_HELPERS)


def _cfg(config, key, default):
    if config and key in config:
        return config[key]
    return default


def define_columns(df, sample=None, args=None, config=None):
    min_gen = float(_cfg(config, "min_gen_fraction", 0.5))
    min_other = float(_cfg(config, "min_other_fraction", 0.5))
    veto_dr = float(_cfg(config, "lepton_veto_dr", 0.4))
    lep_pt = float(_cfg(config, "lepton_min_pt", 10.0))

    # generator muons of the Z: gen jets around them are not hadronic jets
    df = (
        df.Define("TJ_muMask", "abs(GenPart_pdgId) == 13 && GenPart_status == 1 && GenPart_pt > %g" % lep_pt)
        .Define("TJ_muEta", "GenPart_eta[TJ_muMask]")
        .Define("TJ_muPhi", "GenPart_phi[TJ_muMask]")
        .Define("GenJet_nearLepton", "truejesNearAny(GenJet_eta, GenJet_phi, TJ_muEta, TJ_muPhi, %g)" % veto_dr)
        .Define("GenJet_absEta", "abs(GenJet_eta)")
        .Define("GenJet_hadronic", "GenJet_nearLepton == 0")
    )

    # The purity requirement (simFraction / recoFraction) applies to the plain
    # pt ratio only: the signal-only ratio (*Sig levels) and the shared-energy
    # response count the gen jet's own energy by construction, so a pile-up
    # dominated reconstructed jet is still a valid measurement for them.
    for level, (table, other, ratio) in LEVELS.items():
        mo = 0.0 if ratio == "signalPtRatio" else min_other
        df = df.Define(
            "R_%s" % level,
            "truejesBestRatio(GenJet_pt, {t}_genJetIdx, {t}_bestForGen, {t}_genFraction, {t}_{o}, {t}_{r}, {mg}f, {mo}f)".format(
                t=table, o=other, r=ratio, mg=min_gen, mo=mo
            ),
        )
    columns = [str(c) for c in df.GetColumnNames()]
    corrected = []
    if "PFJetPuppi_jecL1L2L3" in columns:
        for level, (base, factor) in CORRECTED_LEVELS.items():
            table, other, ratio = LEVELS[base]
            mo = 0.0 if ratio == "signalPtRatio" else min_other
            df = df.Define("TJ_factor_%s" % level, factor)
            df = df.Define(
                "R_%s" % level,
                "truejesBestRatioScaled(GenJet_pt, {t}_genJetIdx, {t}_jetIdx, {t}_bestForGen, {t}_genFraction, {t}_{o}, {t}_{r}, TJ_factor_{l}, {mg}f, {mo}f)".format(
                    t=table, o=other, r=ratio, l=level, mg=min_gen, mo=mo
                ),
            )
            corrected.append(level)
    else:
        print("truejes: no PFJetPuppi_jecL1L2L3 column, corrected Puppi levels skipped")
    for level in SHARED_LEVELS:
        table, other, _ = LEVELS[level]
        df = df.Define(
            "S_%s" % level,
            "truejesBestShared(GenJet_pt, GenJet_eta, GenJet_mass, {t}_genJetIdx, {t}_bestForGen, {t}_genFraction, {t}_{o}, {t}_sharedEnergy, {mg}f, 0.0f)".format(
                t=table, o=other, mg=min_gen
            ),
        )

    for region, (lo, hi) in ETA_REGIONS.items():
        mask = "GenJet_hadronic && GenJet_absEta >= %g && GenJet_absEta < %g" % (lo, hi)
        df = df.Define("TJ_mask_%s" % region, mask)
        df = df.Define("GenPt_%s" % region, "GenJet_pt[TJ_mask_%s]" % region)
        for level in list(LEVELS) + corrected:
            r = "R_%s" % level
            # matched flag over all hadronic gen jets of the region (efficiency vs pt)
            df = df.Define("M_%s_%s" % (level, region), "truejesMatchedFlag(%s[TJ_mask_%s])" % (r, region))
            # matched pairs only: response and the gen pt it belongs to
            sel = "TJ_mask_%s && %s > 0" % (region, r)
            df = df.Define("Rm_%s_%s" % (level, region), "%s[%s]" % (r, sel))
            df = df.Define("GenPtm_%s_%s" % (level, region), "GenJet_pt[%s]" % sel)
            for lo_pt, hi_pt in PT_BINS:
                lab = pt_bin_label(lo_pt, hi_pt)
                df = df.Define(
                    "Rm_%s_%s_%s" % (level, region, lab),
                    "%s[%s && GenJet_pt >= %g && GenJet_pt < %g]" % (r, sel, lo_pt, hi_pt),
                )
        for level in SHARED_LEVELS:
            sv = "S_%s" % level
            sel = "TJ_mask_%s && %s > 0" % (region, sv)
            df = df.Define("Sm_%s_%s" % (level, region), "%s[%s]" % (sv, sel))
            df = df.Define("GenPtS_%s_%s" % (level, region), "GenJet_pt[%s]" % sel)
    return df


def define_weighted_columns(df, sample=None, args=None, config=None, event_weight=None):
    # unweighted: one DY sample, jets are counted as they come
    if "eventWeight" not in [str(c) for c in df.GetColumnNames()]:
        df = df.Define("eventWeight", "1.0")
    return df


def get_regions(sample=None, args=None, config=None):
    return {"all": {"cuts": ["nGenJet > 0"]}}
