import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.AlCa.GlobalTag import GlobalTag

options = VarParsing("analysis")

options.register("output",
                "pico.root",
                VarParsing.multiplicity.singleton,
                VarParsing.varType.string,
                "Output PicoAOD file"
                )

options.register("globalTag",
                 "auto:run2_mc",
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 "GlobalTag"
                 )

options.register("tables", 
                 "event,muons,electrons,jets,met,custom_objects",
                 VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "Comma-separated table groups"
                 )

options.register('dumpPython', None,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.string,
              'path to python file with content of cms.Process')

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

# input EDM files [primary]
if options.inputFiles:
  process.source.fileNames = options.inputFiles
else:
  process.source.fileNames = [
    '/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root'
  ]

# input EDM files [secondary]
if not hasattr(process.source, 'secondaryFileNames'):
  process.source.secondaryFileNames = cms.untracked.vstring()

if options.secondaryInputFiles:
  process.source.secondaryFileNames = options.secondaryInputFiles
else:
  process.source.secondaryFileNames = [
    #'/store/mc/Run3Winter23Digi/QCD_PT-15to7000_TuneCP5_13p6TeV_pythia8/GEN-SIM-RAW/FlatPU0to80_126X_mcRun3_2023_forPU65_v1-v1/2560000/00d203d8-3ef3-4ca2-884d-a6b2f3bfbb6e.root',
  ]

isMC=False
if "/mc/" in process.source.fileNames[0]:
  isMC=True
  print("Identified the sample is MC")
else:
  print("Identified the sample is DATA")

from Reco2Pico.PicoProducer.pico_cff import buildPicoSequence

enabled_tables = [x.strip() for x in options.tables.split(",") if x.strip()]
process.picoSequence = buildPicoSequence(process, enabled_tables, isMC)

process.p = cms.Path(process.picoSequence)

process.out = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string(options.output),
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

# dump content of cms.Process to python file
if options.dumpPython is not None:
   open(options.dumpPython, 'w').write(process.dumpPython())
