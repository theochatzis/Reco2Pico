"""
phase2_gun: workflow-specific VarParsing options and hooks, used by
gun_varparsing_tail.py through common.varparsing.apply_varparsing.

Three thresholds decide down to which energy a gun particle is visible in the
hgcalval-nano ntuple; all three are options here so that one command line
controls them (see "Low-energy thresholds" in README.md):
  pMin        gun |p| lower edge (GEN step)                          default 0.2 GeV
The eta window is [etaMin, etaMax] in |eta|; etaSide picks the endcap (both =
alternate the sign per job, so a dataset of N jobs has N/2 jobs per endcap).
  cpMinE      CaloTruthAccumulator MinEnergy (step 2, process.mix.digitizers.calotruth):
              no CaloParticle (hence no ticlSimTrackstersfromCPs, no CP associations)
              below it. Release default 0.5 GeV; -1 keeps the release value.   default 0.1 GeV
  genPtMin    pT cut of the HGCalGenPart table (NANO:@HGCALVal, hgcalGenPartTable.cut).
              Release default "status==1 && pt > 0.5"; at 1.6 < eta < 2.9 that is
              |p| > 1.3-4.6 GeV. -1 keeps the release cut.                      default 0 (status==1 only)
"""
import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

_T = VarParsing.VarParsing.varType

GUN_OPTIONS = (
    ('pdgId',    211,   _T.int,   'gun particle PDG id'),
    ('pMin',     0.2,   _T.float, 'gun minimum |p| [GeV]'),
    ('pMax',     200.0, _T.float, 'gun maximum |p| [GeV]'),
    ('etaMin',   1.6,   _T.float, 'gun minimum |eta|'),
    ('etaMax',   2.9,   _T.float, 'gun maximum |eta|'),
    ('etaSide',  'both', _T.string, 'endcap: both (even jobs +eta, odd jobs -eta), pos or neg'),
    ('cpMinE',   0.1,   _T.float, 'CaloParticle creation threshold MinEnergy [GeV] (step 2 calotruth; -1 = release default 0.5)'),
    ('genPtMin', 0.0,   _T.float, 'pT cut of the HGCalGenPart nano table [GeV] (0 = status==1 only; -1 = release default 0.5)'),
)


def eta_window(opts, job):
    """(MinEta, MaxEta) of this job. The release guns draw eta uniformly in one
    interval, so both endcaps are covered by alternating the sign per job:
    etaSide=both -> even jobs [etaMin, etaMax], odd jobs [-etaMax, -etaMin]."""
    lo, hi = sorted((abs(float(opts.etaMin)), abs(float(opts.etaMax))))
    side = str(opts.etaSide).lower()
    if side not in ('both', 'pos', 'neg'):
        raise ValueError('etaSide must be both, pos or neg (got {!r})'.format(opts.etaSide))
    negative = side == 'neg' or (side == 'both' and job % 2 == 1)
    return (-hi, -lo) if negative else (lo, hi)


def apply_gun(process, opts, job):
    """Apply species and kinematics to process.generator.PGunParameters (GEN step only)."""
    pg = process.generator.PGunParameters
    pg.PartID = cms.vint32(int(opts.pdgId))
    if hasattr(pg, 'ProbParts'):
        pg.ProbParts = cms.vdouble(1.0)
    pg.MinP = cms.double(float(opts.pMin))
    pg.MaxP = cms.double(float(opts.pMax))
    eta_lo, eta_hi = eta_window(opts, job)
    pg.MinEta = cms.double(eta_lo)
    pg.MaxEta = cms.double(eta_hi)
    return 'pdgId={} p=[{},{}] eta=[{},{}] (etaSide={})'.format(opts.pdgId, opts.pMin, opts.pMax, eta_lo, eta_hi, opts.etaSide)


def apply_gun_thresholds(process, opts, job):
    """Every step: lower the sim/nano thresholds that would hide low-energy gun particles.

    * step 2 (mixing): process.mix.digitizers.calotruth.MinEnergy = cpMinE
    * ntuple step (NANO:@HGCALVal): process.hgcalGenPartTable.cut = 'status==1 [&& pt > genPtMin]'
    Steps without these modules are left untouched.
    """
    detail = []
    cp_min = float(opts.cpMinE)
    mix = getattr(process, 'mix', None)
    calotruth = getattr(getattr(mix, 'digitizers', None), 'calotruth', None) if mix is not None else None
    if calotruth is not None and hasattr(calotruth, 'MinEnergy'):
        if cp_min >= 0:
            calotruth.MinEnergy = cms.double(cp_min)
        detail.append('calotruth.MinEnergy={}'.format(calotruth.MinEnergy.value()))

    gen_pt = float(opts.genPtMin)
    table = getattr(process, 'hgcalGenPartTable', None)
    if table is not None and hasattr(table, 'cut'):
        if gen_pt >= 0:
            table.cut = cms.string('status==1' + (' && pt > {}'.format(gen_pt) if gen_pt > 0 else ''))
        detail.append('hgcalGenPartTable.cut="{}"'.format(table.cut.value()))
    return ' '.join(detail)
