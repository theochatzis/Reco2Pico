"""
samples_workflows.common.varparsing
===================================

The bdriver command-line contract for every cmsRun step of a sample chain.

bdriver runs step 1 as
    cmsRun cfg.py <workflow args> maxEvents=M skipEvents=0 inputFiles=<virtual or real> output=step1_out_NNN.root
and every following step of the steps manifest as
    cmsRun cfg.py <args> inputFiles=file:<previous> secondaryInputFiles= maxEvents=-1 skipEvents=0 output=<next>

Any cfg that is part of a chain (cmsDriver-generated or hand-written) calls

    from Reco2Pico.PicoProducer.samples_workflows.common.varparsing import apply_varparsing
    process = apply_varparsing(process)                       # plain step
    process = apply_varparsing(process, extra_options=OPTS,   # step with workflow options
                               on_gen=my_gen_hook, tag='phase2_gun')

which
  * registers skipEvents, output, seed (+ the workflow's extra_options) on top of
    VarParsing('analysis') and parses the command line once;
  * derives a job index from job(\\d+) in the first inputFiles entry (gun://jobNNN),
    or from bdriver's step1_out_NNN.root naming, or from skipEvents // maxEvents;
  * GEN steps (EmptySource + process.generator): sets initialSeed = (seed or 12345)
    + 1000*job on every RandomNumberGeneratorService PSet, source.firstEvent =
    1 + maxEvents*job, source.firstLuminosityBlock = 1 + job, then calls
    on_gen(process, opts, job) for workflow-specific generator settings;
  * PoolSource steps: sets fileNames / secondaryFileNames / skipEvents and offsets
    the seeds the same way when a job index was found in inputFiles (so that
    e.g. pile-up mixing differs between jobs);
  * renames the single output module (and TFileService, if any) to output=.

extra_options: iterable of (name, default, VarParsing.varType.*, doc).
Options are singletons; re-registration of an existing one is tolerated.
"""
import re

import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

DEFAULT_SEED = 12345
SEED_STRIDE = 1000
REQUIRED_GEN_SEEDS = ('generator', 'VtxSmeared', 'g4SimHits', 'mix')


def _register(opts, name, default, vtype, doc):
    try:
        opts.register(name, default, VarParsing.VarParsing.multiplicity.singleton, vtype, doc)
    except RuntimeError as err:
        if 're-register' not in str(err):
            raise


def parse_options(extra_options=()):
    """VarParsing('analysis') + skipEvents/output/seed + extra_options, parsed."""
    opts = VarParsing.VarParsing('analysis')
    _register(opts, 'skipEvents', 0, VarParsing.VarParsing.varType.int, 'number of events to skip (PoolSource steps)')
    _register(opts, 'output', '', VarParsing.VarParsing.varType.string, 'output file name (overrides cmsDriver --fileout)')
    _register(opts, 'seed', 0, VarParsing.VarParsing.varType.int,
              'base random seed (0 -> {}); offset by {}*job'.format(DEFAULT_SEED, SEED_STRIDE))
    for name, default, vtype, doc in extra_options:
        _register(opts, name, default, vtype, doc)
    opts.parseArguments()
    return opts


def job_index(opts, input_files):
    """(job, found_in_input): job(\\d+) or out_(\\d+).root in the first input, else skipEvents // maxEvents."""
    if input_files:
        match = re.search(r'job(\d+)', input_files[0])
        if match is None:
            match = re.search(r'out_(\d+)\.root$', input_files[0])
        if match is not None:
            return int(match.group(1)), True
    if opts.maxEvents > 0:
        return int(opts.skipEvents) // int(opts.maxEvents), False
    return int(opts.skipEvents), False


def apply_seeds(process, seed):
    """Set initialSeed on every module PSet of RandomNumberGeneratorService; returns the names touched."""
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


def set_output(process, filename, tag):
    """Rename the single output module (and TFileService) to filename."""
    outmods = list(process.outputModules_().items())
    if len(outmods) > 1:
        raise RuntimeError('{}: more than one output module ({}); one output per step is required'.format(
            tag, ', '.join(name for name, _ in outmods)))
    for name, mod in outmods:
        mod.fileName = cms.untracked.string(filename)
        print('{}: {}.fileName = {}'.format(tag, name, filename))
    if hasattr(process, 'TFileService'):
        process.TFileService.fileName = cms.string(filename)


def apply_varparsing(process, extra_options=(), on_gen=None, tag='samples_workflows'):
    opts = parse_options(extra_options)
    input_files = [f for f in list(opts.inputFiles) if f]
    secondary_files = [f for f in list(opts.secondaryInputFiles) if f]
    job, job_from_input = job_index(opts, input_files)
    seed = (int(opts.seed) or DEFAULT_SEED) + SEED_STRIDE * job

    process.maxEvents.input = cms.untracked.int32(int(opts.maxEvents))

    is_gen = (process.source.type_() == 'EmptySource') and hasattr(process, 'generator')
    if is_gen:
        seeded = apply_seeds(process, seed)
        for required in REQUIRED_GEN_SEEDS:
            if required not in seeded and hasattr(process, required):
                raise RuntimeError('{}: RandomNumberGeneratorService has no PSet for {}'.format(tag, required))
        first_event = 1 + (int(opts.maxEvents) * job if opts.maxEvents > 0 else 0)
        process.source.firstEvent = cms.untracked.uint32(first_event)
        process.source.firstLuminosityBlock = cms.untracked.uint32(1 + job)
        detail = on_gen(process, opts, job) if on_gen is not None else ''
        print('{}: GEN job={} seed={} firstEvent={} firstLumi={} {} rng={}'.format(
            tag, job, seed, first_event, 1 + job, detail or '', ','.join(seeded)))
    else:
        if input_files:
            process.source.fileNames = cms.untracked.vstring(input_files)
        if secondary_files:
            process.source.secondaryFileNames = cms.untracked.vstring(secondary_files)
        process.source.skipEvents = cms.untracked.uint32(int(opts.skipEvents))
        seeded = apply_seeds(process, seed) if job_from_input else []
        print('{}: job={} inputFiles={} skipEvents={} seed={} rng={}'.format(
            tag, job, input_files, opts.skipEvents, seed if seeded else '<default>', ','.join(seeded) or '-'))

    if opts.output:
        set_output(process, opts.output, tag)

    return process
