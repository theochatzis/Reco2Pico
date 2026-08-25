import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.AlCa.GlobalTag import GlobalTag

opts = VarParsing("analysis")

opts.register("output",
                "pico.root",
                VarParsing.multiplicity.singleton,
                VarParsing.varType.string,
                "Output PicoAOD file"
                )

opts.register('skipEvents', 0,
               VarParsing.multiplicity.singleton,
               VarParsing.varType.int,
               'number of events to be skipped'
               )

opts.register('lumis', None,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.string,
              'path to .json with list of luminosity sections'
              )

opts.register("globalTag",
                 "auto:phase1_2025_realistic",
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 "GlobalTag"
                 )

opts.register("tables", 
                 "event,muons,electrons,jets,met,vertices",
                 VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "Comma-separated table groups"
                 )

opts.register( "skim",
                  "",
                  VarParsing.multiplicity.singleton,
                  VarParsing.varType.string,
                  "Comma-separated skim names, e.g. 'zjet'. Empty string means no skim."
)

opts.register('dumpPython', None,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.string,
              'path to python file with content of cms.Process')

# For re-applying JECs , re-running PUPPI
opts.register("rerunPUPPI",
                 False,
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.bool,
                 "Rerun PUPPI, recluster AK4 PUPPI jets, and build new PAT jets for Pico"
                 )

opts.register("reApplyJEC",
                 False,
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.bool,
                 "Re-apply JECs to the Pico jet collection using the GlobalTag or a local SQLite DB"
                 )

opts.register("jecDBFile",
                 "",
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 "Optional local SQLite DB file for JECs. Leave empty to use the GlobalTag"
                 )

opts.register("jecDBTag",
                 "",
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 "Optional JetCorrectionsRecord tag in the local SQLite DB"
                 )


opts.parseArguments()

process = cms.Process("PICO")

process.load("Configuration.StandardSequences.Services_cff")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.Geometry.GeometryDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.GlobalTag = GlobalTag(process.GlobalTag, opts.globalTag, "")

# === Setup the source ===
process.source = cms.Source("PoolSource", fileNames=cms.untracked.vstring(opts.inputFiles))
process.source.skipEvents = cms.untracked.uint32(opts.skipEvents)
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(opts.maxEvents))
process.MessageLogger.cerr.FwkReport.reportEvery = 100

# select luminosity sections from .json file
if opts.lumis is not None:
   import FWCore.PythonUtilities.LumiList as LumiList
   print(f'Selecting lumis from JSON file: {opts.lumis}')
   process.source.lumisToProcess = LumiList.LumiList(filename = opts.lumis).getVLuminosityBlockRange()

# === Setup the inputs ===
# input EDM files [primary]
if opts.inputFiles:
  process.source.fileNames = opts.inputFiles
else:
  process.source.fileNames = [
    '/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root'
  ]

# input EDM files [secondary]
if not hasattr(process.source, 'secondaryFileNames'):
  process.source.secondaryFileNames = cms.untracked.vstring()

if opts.secondaryInputFiles:
  process.source.secondaryFileNames = opts.secondaryInputFiles
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

# === Skim helper ===
def loadSkims(process, skimNames, isMC):
    """
    Load skim fragments from:

        Reco2Pico/PicoProducer/python/skims/<skim>_cff.py

    Each fragment must define:

        setup(process, isMC=False)

    and return a cms.Sequence.
    """
    import importlib

    skimNames = [x.strip() for x in skimNames.split(",") if x.strip()]

    if len(skimNames) == 0:
        return cms.Sequence()

    skimSequence = cms.Sequence()

    for skimName in skimNames:
        moduleName = "Reco2Pico.PicoProducer.skims.%s_cff" % skimName

        try:
            skimModule = importlib.import_module(moduleName)
        except ImportError as err:
            raise RuntimeError(
                "Could not import skim '%s'. Expected file:\n"
                "  Reco2Pico/PicoProducer/python/skims/%s_cff.py\n"
                "Original error:\n  %s"
                % (skimName, skimName, err)
            )

        if not hasattr(skimModule, "setup"):
            raise RuntimeError(
                "Skim module '%s' does not define setup(process, isMC=False)"
                % moduleName
            )

        print("Loading skim: %s from %s" % (skimName, moduleName))
        skimSequence += skimModule.setup(process, isMC=isMC)

    return skimSequence


# === Tables producers ===
from Reco2Pico.PicoProducer.objects.pico_puppi_jets_cff import setupPuppiPatJetsForPico
jet_source_for_pico = "slimmedJetsPuppi"
process, jet_source_for_pico = setupPuppiPatJetsForPico(
    process,
    rerunPUPPI=opts.rerunPUPPI,
    reApplyJEC=opts.reApplyJEC,
    jetSource=jet_source_for_pico,
    candName="packedPFCandidates", # Input candidates for the rerun PUPPI producer in case of rerunPUPPI
    vertexName="offlineSlimmedPrimaryVertices", # Input vertices for the rerun PUPPI producer and JEC update
    pfCandidates="packedPFCandidates", # Input candidates in case of reApplyJEC
    svSource="slimmedSecondaryVertices", # Secondary vertices used by PAT jet tools
    jecPayload="AK4PFPuppi", # JEC payload/label, e.g. AK4PFPuppi
    jecLevels=("L1FastJet", "L2Relative", "L3Absolute", "L2L3Residual"),
    jecDBFile=opts.jecDBFile,
    jecDBTag=opts.jecDBTag,
    labelName="PicoPuppiJet", # Label used for the newly produced PAT jet collection
)

from Reco2Pico.PicoProducer.pico_cff import buildPicoSequence
enabled_tables = [x.strip() for x in opts.tables.split(",") if x.strip()]

process.picoSequence = buildPicoSequence(
   process=process, 
   enabled_tables=enabled_tables,
   isMC=isMC,
   jetSrc=jet_source_for_pico,
)

process.skimSequence = loadSkims(process, opts.skim, isMC)

if opts.skim:
    process.p = cms.Path(process.skimSequence * process.picoSequence)
else:
    process.p = cms.Path(process.picoSequence)

process.out = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string(opts.output),
    outputCommands= cms.untracked.vstring(
    "drop *",
    "keep edmTriggerResults_*_*_*", # for trigger decisions and Noise filters
    "keep nanoaodFlatTable_*Table_*_*",
    "keep nanoaodUniqueString_nanoMetadata_*_*",
    ),
    compressionAlgorithm=cms.untracked.string("LZMA"),
    compressionLevel=cms.untracked.int32(4),
    SelectEvents=cms.untracked.PSet( # added this to be able to skim
        SelectEvents=cms.vstring("p")
    ),
)
process.end = cms.EndPath(process.out)
process.schedule = cms.Schedule(process.p, process.end)

# In order to use the rerunPUPPI and reApplyJEC
if hasattr(process, "reco2picoJetTask"):
    process.schedule.associate(process.reco2picoJetTask)

if hasattr(process, "patAlgosToolsTask"):
    process.schedule.associate(process.patAlgosToolsTask)

# dump content of cms.Process to python file
if opts.dumpPython is not None:
   open(opts.dumpPython, 'w').write(process.dumpPython())
