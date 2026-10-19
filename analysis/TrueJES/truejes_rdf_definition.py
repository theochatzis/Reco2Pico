"""
TrueJES: jet energy scale decomposed along the truth ladder.

RDF definition for SkimRDFAnalysisBase/run_analysis.py on the Reco2Pico
run3_rawsim Picos (groups genparts, sim, simcalo, recojets).

For every GenJet (anti-kt 0.4, no neutrinos, re-clustered in the Pico job) the
response pT/pT_GEN is taken at every step of the ladder from the ancestry
match tables, with the pair that is best for the gen jet and passes the two
fraction requirements (analysis config: min_gen_fraction, min_other_fraction):

    Sim          SimJet          the calorimeter-entrance particles with their production
                                 momenta: decays, conversions, interactions in the tracker (Geant4)
    SimBoundary  SimBoundaryJet  the same particles with their momentum at the calorimeter face:
                                 energy loss in the tracker material and bending
    SimCalo      SimCaloJet      the calorimeter response (sim deposits per entrance particle)
    SimCaloCell  SimCaloCellJet  the same deposits clustered as cells (calorimeter geometry)
    SimPF        SimPFJet        ideal particle flow (perfect tracking + deposits)
    PF       PFJet        reconstructed, raw, all pile-up           [PFSig: signal part only]
    CHS      PFJetCHS     reconstructed, raw, charged-hadron subtraction [CHSSig]
    Puppi    PFJetPuppi   reconstructed, raw, Puppi                 [PuppiSig]

S_<level> is the shared-energy response sharedEnergy / E_GEN: only the energy of
the matched jet that descends from the gen jet. It is immune to the foreign
energy (underlying event, neighbouring jets) that a matched jet picks up, which
pushes the plain pT ratio above one at low pT.

Pile-up truth (classically mixed chain, run3_mix): three more levels,
SimCaloCellPU (cells with signal + in-time pile-up), SimPFPU (ideal PF of
signal + pile-up) and SimPFPUCHS (the same after a perfect charged-hadron
subtraction), and the split of the offsets into the part attributed to in-time
pile-up particles (PFCandTruth_puFraction) and the residual (noise,
out-of-time pile-up, calibration). On a premixed sample these are empty.

Offsets: for the reconstructed jets the unattributed part of every constituent
(clustering weight times (1 - signalFraction) times pT) is summed per jet and
per PF candidate type (charged hadrons, photons, neutral hadrons, HF hadrons,
HF EM, leptons/other, total): the pile-up and noise offset of the jet with its
composition, versus pT_GEN per eta region and versus |eta_GEN| per pT_GEN bin.

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
    "SimBoundary": ("SimBoundaryGenJetMatch", "simFraction", "ptRatio"),
    "SimCalo":  ("SimCaloGenJetMatch", "simFraction",  "ptRatio"),
    "SimCaloCell": ("SimCaloCellGenJetMatch", "simFraction", "ptRatio"),
    "SimPF":    ("SimPFGenJetMatch",   "simFraction",  "ptRatio"),
    # with the pile-up truth of the classically mixed chain (run3_mix): empty otherwise
    "SimCaloCellPU": ("SimCaloCellPUGenJetMatch", "simFraction", "ptRatio"),
    "SimPFPU":       ("SimPFPUGenJetMatch",       "simFraction", "ptRatio"),
    "SimPFPUCHS":    ("SimPFPUCHSGenJetMatch",    "simFraction", "ptRatio"),
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
SHARED_LEVELS = ["Sim", "SimBoundary", "SimCalo", "SimCaloCell", "SimPF", "SimCaloCellPU", "SimPFPU", "SimPFPUCHS", "PF", "CHS", "Puppi"]

ETA_REGIONS = {
    "Incl": (0.0, 5.0),
    "HB":   (0.0, 1.3),
    "HE1":  (1.3, 2.5),
    "HE2":  (2.5, 3.0),
    "HF":   (3.0, 5.0),
}

# reconstructed collections with constituents and candidate attribution (offsets)
OFFSET_COLLECTIONS = {"PF": "PFJet", "CHS": "PFJetCHS", "Puppi": "PFJetPuppi"}
OFFSET_TYPES = ["chHad", "photon", "neuHad", "hfHad", "hfEM", "other", "total"]
SIMPF_KINDS = ["chargedTrack", "neutralDeposit", "chargedDeposit", "total"]
GEN_TYPES = ["chHad", "photon", "neuHad", "other", "total"]
# the standard JEC |eta| bins
ETA_EDGES = [0.0, 0.261, 0.522, 0.783, 1.044, 1.305, 1.479, 1.653, 1.930, 2.172, 2.322, 2.500,
             2.650, 2.853, 2.964, 3.139, 3.489, 3.839, 4.191, 4.538, 4.889, 5.191]

# gen-pt bins of the response distributions (low pt is the focus)
PT_BINS = [(5, 8), (8, 13), (13, 20), (20, 30), (30, 50), (50, 100), (100, 300)]

# TProfile / TH2 edges of the response vs gen pt
PT_EDGES = [5, 6.5, 8, 10, 13, 16, 20, 25, 30, 40, 50, 70, 100, 150, 300]


def pt_bin_label(lo, hi):
    return "pt%dto%d" % (lo, hi)


CPP_HELPERS = r"""
#include "ROOT/RVec.hxx"
#include <algorithm>
#include <cmath>
#include <cstdlib>
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

// ---- offsets: the unattributed part of a reconstructed jet, by PF candidate type ----
// types: 0 charged hadrons, 1 photons, 2 neutral hadrons, 3 HF hadrons, 4 HF EM, 5 leptons and other, 6 total
const int TJ_NTYPES = 7;
int truejesCandType(int pdg) {
  const int a = std::abs(pdg);
  if (a == 211) return 0;
  if (a == 22) return 1;
  if (a == 130) return 2;
  if (a == 1) return 3;
  if (a == 2) return 4;
  return 5;
}
// per jet (jet-major, TJ_NTYPES entries each): scalar sum of w_c (1 - f_c^sig) pT_c over the constituents
RVec<float> truejesJetOffsets(int nJets, const RVec<int>& constJet, const RVec<int>& constCand, const RVec<float>& constW,
                              const RVec<float>& candPt, const RVec<int>& candPdg, const RVec<float>& candSig) {
  RVec<float> out((nJets > 0 ? nJets : 0) * TJ_NTYPES, 0.f);
  for (size_t i = 0; i < constJet.size(); ++i) {
    const int j = constJet[i], c = constCand[i];
    if (j < 0 || j >= nJets || c < 0 || size_t(c) >= candPt.size()) continue;
    const float off = constW[i] * (1.f - candSig[c]) * candPt[c];
    out[j * TJ_NTYPES + truejesCandType(candPdg[c])] += off;
    out[j * TJ_NTYPES + TJ_NTYPES - 1] += off;
  }
  return out;
}
// the same split into what is attributed to in-time pile-up particles (PFCandTruth_puFraction) and the
// residual (noise, out-of-time pile-up, calibration): per jet 2 x TJ_NTYPES entries, pile-up first
RVec<float> truejesJetOffsetsPU(int nJets, const RVec<int>& constJet, const RVec<int>& constCand, const RVec<float>& constW,
                                const RVec<float>& candPt, const RVec<int>& candPdg, const RVec<float>& candSig, const RVec<float>& candPU) {
  RVec<float> out((nJets > 0 ? nJets : 0) * 2 * TJ_NTYPES, 0.f);
  for (size_t i = 0; i < constJet.size(); ++i) {
    const int j = constJet[i], c = constCand[i];
    if (j < 0 || j >= nJets || c < 0 || size_t(c) >= candPt.size()) continue;
    const float pu = constW[i] * candPU[c] * candPt[c];
    const float res = constW[i] * std::max(0.f, 1.f - candSig[c] - candPU[c]) * candPt[c];
    const int t = truejesCandType(candPdg[c]);
    out[j * 2 * TJ_NTYPES + t] += pu;
    out[j * 2 * TJ_NTYPES + TJ_NTYPES - 1] += pu;
    out[j * 2 * TJ_NTYPES + TJ_NTYPES + t] += res;
    out[j * 2 * TJ_NTYPES + 2 * TJ_NTYPES - 1] += res;
  }
  return out;
}
// the signal part of a reconstructed jet by candidate type: sum of w_c f_c^sig pT_c (jet-major, TJ_NTYPES each)
RVec<float> truejesJetSignalByType(int nJets, const RVec<int>& constJet, const RVec<int>& constCand, const RVec<float>& constW,
                                   const RVec<float>& candPt, const RVec<int>& candPdg, const RVec<float>& candSig) {
  RVec<float> out((nJets > 0 ? nJets : 0) * TJ_NTYPES, 0.f);
  for (size_t i = 0; i < constJet.size(); ++i) {
    const int j = constJet[i], c = constCand[i];
    if (j < 0 || j >= nJets || c < 0 || size_t(c) >= candPt.size()) continue;
    const float s = constW[i] * candSig[c] * candPt[c];
    out[j * TJ_NTYPES + truejesCandType(candPdg[c])] += s;
    out[j * TJ_NTYPES + TJ_NTYPES - 1] += s;
  }
  return out;
}
// the ideal PF jet by kind of its candidates: 0 charged from momentum, 1 neutral deposit, 2 charged untrackable deposit, 3 total
const int TJ_NKINDS = 4;
RVec<float> truejesSimPFByKind(int nJets, const RVec<int>& candJet, const RVec<int>& candKind, const RVec<float>& candPt) {
  RVec<float> out((nJets > 0 ? nJets : 0) * TJ_NKINDS, 0.f);
  for (size_t c = 0; c < candJet.size(); ++c) {
    const int j = candJet[c];
    if (j < 0 || j >= nJets) continue;
    const int k = candKind[c] % 10;  // pile-up entries (11, 12, 13) count with the same kinds
    const int t = (k == 1) ? 0 : (k == 2 ? 1 : 2);
    out[j * TJ_NKINDS + t] += candPt[c];
    out[j * TJ_NKINDS + TJ_NKINDS - 1] += candPt[c];
  }
  return out;
}
// the gen jet by particle type of its constituents (GenJetConst rows -> GenPart): charged hadrons, photons, neutral hadrons, other, total
const int TJ_NGEN = 5;
int truejesGenType(int pdg) {
  const int a = std::abs(pdg);
  if (a == 22) return 1;
  if (a == 11 || a == 13) return 3;
  if (a == 130 || a == 310 || a == 2112 || a == 3122 || a == 3322 || a == 3212) return 2;  // neutral hadrons (K0, n, Lambda, Xi0, Sigma0 as stable in Geant4 terms)
  return 0;  // charged hadrons (and anything else charged)
}
RVec<float> truejesGenByType(int nJets, const RVec<int>& constJet, const RVec<int>& constGenPart, const RVec<float>& constE,
                             const RVec<int>& genPdg, const RVec<float>& genPt, const RVec<float>& genEnergy) {
  RVec<float> out((nJets > 0 ? nJets : 0) * TJ_NGEN, 0.f);
  for (size_t i = 0; i < constJet.size(); ++i) {
    const int j = constJet[i], g = constGenPart[i];
    if (j < 0 || j >= nJets) continue;
    // pt of the constituent: from the GenPart row when known, else energy as a proxy (pruned away)
    float pt = constE[i];
    int type = 0;
    if (g >= 0 && size_t(g) < genPdg.size()) { pt = genPt[g]; type = truejesGenType(genPdg[g]); }
    out[j * TJ_NGEN + type] += pt;
    out[j * TJ_NGEN + TJ_NGEN - 1] += pt;
  }
  return out;
}
// entry t of every jet's nt-block
RVec<float> truejesJetSlice(const RVec<float>& values, int nJets, int nt, int t) {
  RVec<float> out(nJets > 0 ? nJets : 0, 0.f);
  for (int j = 0; j < nJets; ++j) {
    const size_t k = size_t(j) * nt + t;
    if (k < values.size()) out[j] = values[k];
  }
  return out;
}
// one per-jet quantity transferred to the gen jets through the best pair (genFraction requirement only); -1 unmatched
RVec<float> truejesBestJetValue(const RVec<float>& genPt, const RVec<int>& genIdx, const RVec<int>& jetIdx,
                                const RVec<unsigned char>& bestForGen, const RVec<float>& genFrac,
                                const RVec<float>& values, int nt, int t, float minGenFrac) {
  RVec<float> out(genPt.size(), -1.f);
  for (size_t i = 0; i < genIdx.size(); ++i) {
    const int g = genIdx[i], j = jetIdx[i];
    if (g < 0 || size_t(g) >= out.size() || !bestForGen[i] || genFrac[i] < minGenFrac || j < 0) continue;
    const size_t k = size_t(j) * nt + t;
    if (k < values.size()) out[g] = values[k];
  }
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
    columns = [str(c) for c in df.GetColumnNames()]
    for level, (table, other, ratio) in LEVELS.items():
        if "%s_genJetIdx" % table not in columns:  # e.g. the pile-up truth jets on a premixed sample
            print("truejes: no %s table, level %s left empty" % (table, level))
            df = df.Define("R_%s" % level, "ROOT::RVec<float>(GenJet_pt.size(), -1.f)")
            continue
        mo = 0.0 if ratio == "signalPtRatio" else min_other
        df = df.Define(
            "R_%s" % level,
            "truejesBestRatio(GenJet_pt, {t}_genJetIdx, {t}_bestForGen, {t}_genFraction, {t}_{o}, {t}_{r}, {mg}f, {mo}f)".format(
                t=table, o=other, r=ratio, mg=min_gen, mo=mo
            ),
        )
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
        if "%s_genJetIdx" % table not in columns:
            df = df.Define("S_%s" % level, "ROOT::RVec<float>(GenJet_pt.size(), -1.f)")
            continue
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

    # ---- offsets: unattributed pt of the matched reconstructed jet, by candidate type ----
    if "PFJetConst_jetIdx" in columns and "PFCandTruth_signalFraction" in columns:
        for coll, table in OFFSET_COLLECTIONS.items():
            df = df.Define(
                "TJ_off_%s" % coll,
                "truejesJetOffsets((int)n{t}, {t}Const_jetIdx, {t}Const_pfCandIdx, {t}Const_weight, PFCand_pt, PFCand_pdgId, PFCandTruth_signalFraction)".format(t=table),
            )
            for k, typ in enumerate(OFFSET_TYPES):
                df = df.Define(
                    "O_%s_%s" % (coll, typ),
                    "truejesBestJetValue(GenJet_pt, {m}_genJetIdx, {m}_jetIdx, {m}_bestForGen, {m}_genFraction, TJ_off_{c}, {nt}, {k}, {mg}f)".format(
                        m=table + "GenMatch", c=coll, nt=len(OFFSET_TYPES), k=k, mg=min_gen
                    ),
                )
            df = df.Define("TJ_offm_%s" % coll, "O_%s_total >= 0" % coll)
            # the true in-time pile-up and the residual (classically mixed chain; zeros otherwise)
            if "PFCandTruth_puFraction" in columns:
                df = df.Define(
                    "TJ_offpu_%s" % coll,
                    "truejesJetOffsetsPU((int)n{t}, {t}Const_jetIdx, {t}Const_pfCandIdx, {t}Const_weight, PFCand_pt, PFCand_pdgId, PFCandTruth_signalFraction, PFCandTruth_puFraction)".format(t=table),
                )
            else:
                df = df.Define("TJ_offpu_%s" % coll, "ROOT::RVec<float>((int)n{t} * {nt}, 0.f)".format(t=table, nt=2 * len(OFFSET_TYPES)))
            for k, typ in enumerate(OFFSET_TYPES):
                for name, kk in (("OPU", k), ("ORES", len(OFFSET_TYPES) + k)):
                    df = df.Define(
                        "%s_%s_%s" % (name, coll, typ),
                        "truejesBestJetValue(GenJet_pt, {m}_genJetIdx, {m}_jetIdx, {m}_bestForGen, {m}_genFraction, TJ_offpu_{c}, {nt}, {k}, {mg}f)".format(
                            m=table + "GenMatch", c=coll, nt=2 * len(OFFSET_TYPES), k=kk, mg=min_gen
                        ),
                    )
            for region in ETA_REGIONS:
                sel = "TJ_mask_%s && TJ_offm_%s" % (region, coll)
                df = df.Define("GenPtO_%s_%s" % (coll, region), "GenJet_pt[%s]" % sel)
                for typ in OFFSET_TYPES:
                    df = df.Define("Om_%s_%s_%s" % (coll, typ, region), "O_%s_%s[%s]" % (coll, typ, sel))
                    df = df.Define("OPUm_%s_%s_%s" % (coll, typ, region), "OPU_%s_%s[%s]" % (coll, typ, sel))
                    df = df.Define("ORESm_%s_%s_%s" % (coll, typ, region), "ORES_%s_%s[%s]" % (coll, typ, sel))
            for lo_pt, hi_pt in PT_BINS:
                lab = pt_bin_label(lo_pt, hi_pt)
                sel = "GenJet_hadronic && TJ_offm_%s && GenJet_pt >= %g && GenJet_pt < %g" % (coll, lo_pt, hi_pt)
                df = df.Define("GenAbsEtaO_%s_%s" % (coll, lab), "GenJet_absEta[%s]" % sel)
                for typ in OFFSET_TYPES:
                    df = df.Define("Oe_%s_%s_%s" % (coll, typ, lab), "O_%s_%s[%s]" % (coll, typ, sel))
                    df = df.Define("OPUe_%s_%s_%s" % (coll, typ, lab), "OPU_%s_%s[%s]" % (coll, typ, sel))
                    df = df.Define("ORESe_%s_%s_%s" % (coll, typ, lab), "ORES_%s_%s[%s]" % (coll, typ, sel))
        # ---- composition by flavour: the signal part of the reconstructed jet by candidate type ----
        for coll, table in OFFSET_COLLECTIONS.items():
            df = df.Define(
                "TJ_sig_%s" % coll,
                "truejesJetSignalByType((int)n{t}, {t}Const_jetIdx, {t}Const_pfCandIdx, {t}Const_weight, PFCand_pt, PFCand_pdgId, PFCandTruth_signalFraction)".format(t=table),
            )
            for k, typ in enumerate(OFFSET_TYPES):
                df = df.Define(
                    "SG_%s_%s" % (coll, typ),
                    "truejesBestJetValue(GenJet_pt, {m}_genJetIdx, {m}_jetIdx, {m}_bestForGen, {m}_genFraction, TJ_sig_{c}, {nt}, {k}, {mg}f)".format(
                        m=table + "GenMatch", c=coll, nt=len(OFFSET_TYPES), k=k, mg=min_gen
                    ),
                )
            for region in ETA_REGIONS:
                sel = "TJ_mask_%s && TJ_offm_%s" % (region, coll)
                for typ in OFFSET_TYPES:
                    df = df.Define("SGm_%s_%s_%s" % (coll, typ, region), "(SG_%s_%s / GenJet_pt)[%s]" % (coll, typ, sel))
    else:
        print("truejes: no constituent / attribution tables, offsets skipped")
    # ---- composition by flavour: the ideal PF jet by kind and the gen jet by particle type ----
    if "SimPFCand_simPFJetIdx" in columns and "SimPFGenJetMatch_simJetIdx" in columns:
        df = df.Define("TJ_simpfkind", "truejesSimPFByKind((int)nSimPFJet, SimPFCand_simPFJetIdx, SimPFCand_kind, SimPFCand_pt)")
        for k, kind in enumerate(SIMPF_KINDS):
            df = df.Define(
                "SK_%s" % kind,
                "truejesBestJetValue(GenJet_pt, SimPFGenJetMatch_genJetIdx, SimPFGenJetMatch_simJetIdx, SimPFGenJetMatch_bestForGen, SimPFGenJetMatch_genFraction, TJ_simpfkind, {nt}, {k}, {mg}f)".format(
                    nt=len(SIMPF_KINDS), k=k, mg=min_gen
                ),
            )
        df = df.Define("TJ_simpfm", "SK_total >= 0")
        for region in ETA_REGIONS:
            sel = "TJ_mask_%s && TJ_simpfm" % region
            df = df.Define("GenPtK_%s" % region, "GenJet_pt[%s]" % sel)
            for kind in SIMPF_KINDS:
                df = df.Define("SKm_%s_%s" % (kind, region), "(SK_%s / GenJet_pt)[%s]" % (kind, sel))
    else:
        for region in ETA_REGIONS:
            df = df.Define("GenPtK_%s" % region, "ROOT::RVec<float>()")
            for kind in SIMPF_KINDS:
                df = df.Define("SKm_%s_%s" % (kind, region), "ROOT::RVec<float>()")
    if "GenJetConst_genJetIdx" in columns:
        df = df.Define("TJ_gentype", "truejesGenByType((int)nGenJet, GenJetConst_genJetIdx, GenJetConst_genPartIdx, GenJetConst_energy, GenPart_pdgId, GenPart_pt, GenPart_pt)")
        for k, typ in enumerate(GEN_TYPES):
            df = df.Define("GT_%s" % typ, "truejesJetSlice(TJ_gentype, (int)nGenJet, %d, %d)" % (len(GEN_TYPES), k))
        for region in ETA_REGIONS:
            for typ in GEN_TYPES:
                df = df.Define("GTm_%s_%s" % (typ, region), "(GT_%s / GenJet_pt)[TJ_mask_%s]" % (typ, region))
    else:
        for region in ETA_REGIONS:
            for typ in GEN_TYPES:
                df = df.Define("GTm_%s_%s" % (typ, region), "ROOT::RVec<float>()")
    return df


def define_weighted_columns(df, sample=None, args=None, config=None, event_weight=None):
    # unweighted: one DY sample, jets are counted as they come
    if "eventWeight" not in [str(c) for c in df.GetColumnNames()]:
        df = df.Define("eventWeight", "1.0")
    return df


def get_regions(sample=None, args=None, config=None):
    return {"all": {"cuts": ["nGenJet > 0"]}}
