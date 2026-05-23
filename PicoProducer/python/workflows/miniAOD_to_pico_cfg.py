import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.AlCa.GlobalTag import GlobalTag

options = VarParsing("analysis")
options.register("picoOutputFile", "pico.root", VarParsing.multiplicity.singleton, VarParsing.varType.string, "Output PicoAOD file")
options.register("globalTag", "auto:run2_mc", VarParsing.multiplicity.singleton, VarParsing.varType.string, "GlobalTag")
options.register("tables", "event,muons,electrons,jets,met,custom_objects", VarParsing.multiplicity.singleton, VarParsing.varType.string, "Comma-separated table groups")
options.parseArguments()

process = cms.Process("PICO")

process.load("Configuration.StandardSequences.Services_cff")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.Geometry.GeometryDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.GlobalTag = GlobalTag(process.GlobalTag, options.globalTag, "")

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source("PoolSource", fileNames=cms.untracked.vstring(options.inputFiles))
process.MessageLogger.cerr.FwkReport.reportEvery = 100

from Reco2Pico.PicoProducer.pico_cff import buildPicoSequence

enabled_tables = [x.strip() for x in options.tables.split(",") if x.strip()]
process.picoSequence = buildPicoSequence(process, enabled_tables)

process.p = cms.Path(process.picoSequence)

process.out = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string(options.picoOutputFile),
    outputCommands= cms.untracked.vstring(
    "drop *",
    "keep nanoaodFlatTable_*Table_*_*",
    "keep nanoaodUniqueString_nanoMetadata_*_*",
    ),
    compressionAlgorithm=cms.untracked.string("LZMA"),
    compressionLevel=cms.untracked.int32(4),
)
process.end = cms.EndPath(process.out)
process.schedule = cms.Schedule(process.p, process.end)
