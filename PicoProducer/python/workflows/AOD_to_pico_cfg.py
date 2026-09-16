import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.AlCa.GlobalTag import GlobalTag


options = VarParsing("analysis")

options.register(
    "output",
    "pico_AOD.root",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "Output PicoAOD file",
)
options.register(
    "globalTag",
    "",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "GlobalTag. Empty string selects autocond conditions.",
)

options.register(
    "era",
    "Run3_2024",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "CMSSW Era: Run3, Run3_2024, Run3_2025",
)

options.register(
    "geometry",
    "Configuration.StandardSequences.GeometryRecoDB_cff",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "Geometry configuration module",
)

options.register(
    "tables",
    "event,muons,electrons,jets,pfcands,tracks,vertices",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "Comma-separated table groups",
)
options.register(
    "isMC",
    "auto",
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "auto, true, or false",
)
options.register(
    "skipEvents",
    0,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.int,
    "Number of events to skip",
)
options.register(
    "pfCandMinPt",
    0.0,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.float,
    "Minimum pT for PFCand table",
)
options.register(
    "trackMinPt",
    0.0,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.float,
    "Minimum pT for Track table; PFCand_trackIdx is remapped accordingly",
)
options.register(
    "pfClusterMinEnergy",
    0.0,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.float,
    "Minimum PFCluster energy (RECO-only; unused for AOD)",
)
options.register(
    "recHitMinAbsEnergy",
    0.0,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.float,
    "Minimum absolute RecHit energy",
)
options.register(
    "dumpPython",
    None,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    "Path to write process.dumpPython()",
)

options.parseArguments()

if not options.inputFiles:
    raise RuntimeError(
        "No AOD input file specified. Use inputFiles=/store/.../AOD[SIM]/...root"
    )


def resolve_is_mc(mode, files):
    mode = mode.strip().lower()
    if mode in ("true", "1", "yes", "mc"):
        return True
    if mode in ("false", "0", "no", "data"):
        return False
    if mode != "auto":
        raise ValueError("isMC must be auto, true, or false")

    first = str(files[0])
    if "/store/mc/" in first or "/mc/" in first:
        return True
    if "/store/data/" in first or "/data/" in first:
        return False
    raise RuntimeError(
        "Could not infer MC/data from the input path. Pass isMC=true or isMC=false."
    )


isMC = resolve_is_mc(options.isMC, options.inputFiles)
resolvedGlobalTag = options.globalTag or ("auto:phase1_2025_realistic" if isMC else "auto:run3_data")

from Reco2Pico.PicoProducer.tools.eraTools import getEra

process = cms.Process(
    "PICO",
    getEra(options.era),
)

process.load(options.geometry)
process.load("Configuration.StandardSequences.Services_cff")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("TrackingTools.TransientTrack.TransientTrackBuilder_cfi")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.GlobalTag = GlobalTag(process.GlobalTag, resolvedGlobalTag, "")

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(options.inputFiles),
    secondaryFileNames=cms.untracked.vstring(options.secondaryInputFiles),
    skipEvents=cms.untracked.uint32(options.skipEvents),
)
process.MessageLogger.cerr.FwkReport.reportEvery = 100

print("Input tier: AOD")
print("Sample type: %s" % ("MC" if isMC else "DATA"))
print("GlobalTag: %s" % resolvedGlobalTag)

from Reco2Pico.PicoProducer.pico_reco_cff import buildRecoPicoSequence

enabled_tables = [x.strip() for x in options.tables.split(",") if x.strip()]
process.picoSequence = buildRecoPicoSequence(
    process,
    enabled_tables=enabled_tables,
    isMC=isMC,
    inputTier="AOD",
    pfCandMinPt=options.pfCandMinPt,
    trackMinPt=options.trackMinPt,
    pfClusterMinEnergy=options.pfClusterMinEnergy,
    recHitMinAbsEnergy=options.recHitMinAbsEnergy,
)

process.p = cms.Path(process.picoSequence)

process.out = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string(options.output),
    outputCommands=cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_*Table_*_*",
        "keep nanoaodUniqueString_nanoMetadata_*_*",
    ),
    compressionAlgorithm=cms.untracked.string("LZMA"),
    compressionLevel=cms.untracked.int32(4),
)
process.end = cms.EndPath(process.out)
process.schedule = cms.Schedule(process.p, process.end)

if options.dumpPython is not None:
    with open(options.dumpPython, "w") as handle:
        handle.write(process.dumpPython())
