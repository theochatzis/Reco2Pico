
# ===========================================================================
# phase2_gun: VarParsing tail
# Appended verbatim by make_gun_cfgs.sh to every cmsDriver cfg of the chain.
# The marker line above is what makes the append idempotent.
#
# Command-line interface (cmsRun cfg.py key=value ...):
#   maxEvents=N  skipEvents=N  inputFiles=...  secondaryInputFiles=...  output=FILE
#   pdgId=211  pMin=1.0  pMax=200.0  etaMin=1.6  etaMax=2.9  seed=0
#
# GEN step (EmptySource + process.generator):
#   * gun kinematics/species are applied to process.generator.PGunParameters
#   * a job index is derived from the first inputFiles entry matching job(\d+)
#     (fallback: skipEvents // maxEvents), and every RandomNumberGeneratorService
#     module gets initialSeed = (seed or 12345) + 1000*job
#   * source.firstEvent = 1 + maxEvents*job, source.firstLuminosityBlock = 1 + job
# PoolSource steps:
#   * fileNames / secondaryFileNames / skipEvents are set from the command line
#   * RandomNumberGeneratorService seeds are offset the same way when a job index
#     is found in inputFiles, so that e.g. pile-up mixing differs between jobs
# All steps: the single output module (and TFileService, if any) is renamed to
#   the value of output=.
# ===========================================================================
import re as _gun_re
import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as _gun_vpo

_gun_opts = _gun_vpo.VarParsing('analysis')


def _gun_register(name, default, vtype, doc):
    """Register a singleton option, tolerating re-registration."""
    try:
        _gun_opts.register(name, default, _gun_vpo.VarParsing.multiplicity.singleton, vtype, doc)
    except RuntimeError as err:
        if 're-register' not in str(err):
            raise


_gun_register('skipEvents', 0, _gun_vpo.VarParsing.varType.int, 'number of events to skip (PoolSource steps)')
_gun_register('output', '', _gun_vpo.VarParsing.varType.string, 'output file name (overrides cmsDriver --fileout)')
_gun_register('pdgId', 211, _gun_vpo.VarParsing.varType.int, 'gun particle PDG id')
_gun_register('pMin', 1.0, _gun_vpo.VarParsing.varType.float, 'gun minimum |p| [GeV]')
_gun_register('pMax', 200.0, _gun_vpo.VarParsing.varType.float, 'gun maximum |p| [GeV]')
_gun_register('etaMin', 1.6, _gun_vpo.VarParsing.varType.float, 'gun minimum eta')
_gun_register('etaMax', 2.9, _gun_vpo.VarParsing.varType.float, 'gun maximum eta')
_gun_register('seed', 0, _gun_vpo.VarParsing.varType.int, 'base random seed (0 -> 12345); offset by 1000*job')
_gun_opts.parseArguments()

_gun_inputFiles = [f for f in list(_gun_opts.inputFiles) if f]
_gun_secondaryFiles = [f for f in list(_gun_opts.secondaryInputFiles) if f]

# --- job index ------------------------------------------------------------
_gun_job = None
_gun_job_from_input = False
if _gun_inputFiles:
    _gun_match = _gun_re.search(r'job(\d+)', _gun_inputFiles[0])
    if _gun_match is None:
        # bdriver chained steps see inputFiles=file:step1_out_NNN.root
        _gun_match = _gun_re.search(r'out_(\d+)\.root$', _gun_inputFiles[0])
    if _gun_match is not None:
        _gun_job = int(_gun_match.group(1))
        _gun_job_from_input = True
if _gun_job is None:
    if _gun_opts.maxEvents > 0:
        _gun_job = int(_gun_opts.skipEvents) // int(_gun_opts.maxEvents)
    else:
        _gun_job = int(_gun_opts.skipEvents)
_gun_seed = (int(_gun_opts.seed) or 12345) + 1000 * _gun_job


def _gun_apply_seeds(process, seed):
    """Set initialSeed on every module PSet of RandomNumberGeneratorService."""
    if not hasattr(process, 'RandomNumberGeneratorService'):
        return []
    rng = process.RandomNumberGeneratorService
    touched = []
    for name in rng.parameterNames_():
        pset = getattr(rng, name)
        if isinstance(pset, cms.PSet) and hasattr(pset, 'initialSeed'):
            pset.initialSeed = cms.untracked.uint32(seed)
            touched.append(name)
    return touched


# --- max events -----------------------------------------------------------
process.maxEvents.input = cms.untracked.int32(int(_gun_opts.maxEvents))

# --- source ---------------------------------------------------------------
_gun_is_gen = (process.source.type_() == 'EmptySource') and hasattr(process, 'generator')

if _gun_is_gen:
    pg = process.generator.PGunParameters
    pg.PartID = cms.vint32(int(_gun_opts.pdgId))
    if hasattr(pg, 'ProbParts'):
        pg.ProbParts = cms.vdouble(1.0)
    pg.MinP = cms.double(float(_gun_opts.pMin))
    pg.MaxP = cms.double(float(_gun_opts.pMax))
    pg.MinEta = cms.double(float(_gun_opts.etaMin))
    pg.MaxEta = cms.double(float(_gun_opts.etaMax))

    _gun_seeded = _gun_apply_seeds(process, _gun_seed)
    for _gun_required in ('generator', 'VtxSmeared', 'g4SimHits', 'mix'):
        if _gun_required not in _gun_seeded and hasattr(process, _gun_required):
            raise RuntimeError('phase2_gun: RandomNumberGeneratorService has no PSet for ' + _gun_required)

    _gun_firstEvent = 1 + (int(_gun_opts.maxEvents) * _gun_job if _gun_opts.maxEvents > 0 else 0)
    process.source.firstEvent = cms.untracked.uint32(_gun_firstEvent)
    process.source.firstLuminosityBlock = cms.untracked.uint32(1 + _gun_job)
    print('phase2_gun: GEN job={} pdgId={} p=[{},{}] eta=[{},{}] seed={} firstEvent={} firstLumi={} rng={}'.format(
        _gun_job, _gun_opts.pdgId, _gun_opts.pMin, _gun_opts.pMax, _gun_opts.etaMin, _gun_opts.etaMax,
        _gun_seed, _gun_firstEvent, 1 + _gun_job, ','.join(_gun_seeded)))
else:
    if _gun_inputFiles:
        process.source.fileNames = cms.untracked.vstring(_gun_inputFiles)
    if _gun_secondaryFiles:
        process.source.secondaryFileNames = cms.untracked.vstring(_gun_secondaryFiles)
    process.source.skipEvents = cms.untracked.uint32(int(_gun_opts.skipEvents))
    _gun_seeded = _gun_apply_seeds(process, _gun_seed) if _gun_job_from_input else []
    print('phase2_gun: job={} inputFiles={} skipEvents={} seed={} rng={}'.format(
        _gun_job, _gun_inputFiles, _gun_opts.skipEvents, _gun_seed if _gun_seeded else '<default>',
        ','.join(_gun_seeded) or '-'))

# --- output ---------------------------------------------------------------
if _gun_opts.output:
    _gun_outmods = list(process.outputModules_().items())
    if len(_gun_outmods) > 1:
        raise RuntimeError('phase2_gun: more than one output module ({}); one output per step is required'.format(
            ', '.join(name for name, _ in _gun_outmods)))
    for _gun_name, _gun_mod in _gun_outmods:
        _gun_mod.fileName = cms.untracked.string(_gun_opts.output)
        print('phase2_gun: {}.fileName = {}'.format(_gun_name, _gun_opts.output))
    if hasattr(process, 'TFileService'):
        process.TFileService.fileName = cms.string(_gun_opts.output)
# --- end phase2_gun VarParsing tail ---------------------------------------
