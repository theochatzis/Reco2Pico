"""
phase2_gun: workflow-specific VarParsing options and generator hook, used by
gun_varparsing_tail.py through common.varparsing.apply_varparsing.
"""
import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

_T = VarParsing.VarParsing.varType

GUN_OPTIONS = (
    ('pdgId',  211,   _T.int,   'gun particle PDG id'),
    ('pMin',   1.0,   _T.float, 'gun minimum |p| [GeV]'),
    ('pMax',   200.0, _T.float, 'gun maximum |p| [GeV]'),
    ('etaMin', 1.6,   _T.float, 'gun minimum eta'),
    ('etaMax', 2.9,   _T.float, 'gun maximum eta'),
)


def apply_gun(process, opts, job):
    """Apply species and kinematics to process.generator.PGunParameters (GEN step only)."""
    pg = process.generator.PGunParameters
    pg.PartID = cms.vint32(int(opts.pdgId))
    if hasattr(pg, 'ProbParts'):
        pg.ProbParts = cms.vdouble(1.0)
    pg.MinP = cms.double(float(opts.pMin))
    pg.MaxP = cms.double(float(opts.pMax))
    pg.MinEta = cms.double(float(opts.etaMin))
    pg.MaxEta = cms.double(float(opts.etaMax))
    return 'pdgId={} p=[{},{}] eta=[{},{}]'.format(opts.pdgId, opts.pMin, opts.pMax, opts.etaMin, opts.etaMax)
