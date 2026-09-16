# Reco2Pico/PicoProducer/python/objects/pico_puppi_jets_cff.py

"""Helpers to prepare AK4 PUPPI PAT jets for PicoAOD production.

Two modes are supported:
  * re-apply JECs to an existing MiniAOD PAT jet collection, using either the
    GlobalTag or a local SQLite conditions DB;
  * rerun the PUPPI producer, recluster AK4 PF PUPPI jets, and turn them into
    PAT jets.

The returned collection is a PAT jet collection and can be passed directly to
`jetTables(..., src=...)` for PicoAOD output.
"""

import os

import FWCore.ParameterSet.Config as cms
from CondCore.CondDB.CondDB_cfi import CondDB as _CondDB


def _as_input_tag(value):
    if isinstance(value, cms.InputTag):
        return value
    return cms.InputTag(value)


def _jec_levels(levels):
    if isinstance(levels, str):
        return [level.strip() for level in levels.split(",") if level.strip()]
    return list(levels)


def _sqlite_connect(db_file):
    expanded = os.path.expandvars(os.path.expanduser(db_file))
    if expanded.startswith(("sqlite_file:", "frontier://", "oracle://")):
        return expanded
    return "sqlite_file:" + expanded


def _default_jec_tag(jec_payload):
    return "JetCorrectorParametersCollection_%s" % jec_payload


def addLocalJECDB(
    process,
    dbFile,
    jecPayload="AK4PFPuppi",
    jecTag="",
    esSourceName="reco2picoJECESSource",
):
    """Prefer JECs from a local SQLite DB instead of the GlobalTag.

    If `dbFile` is empty, no ESSource is added and the normal GlobalTag JECs
    are used by the PAT jet tools.
    """

    if not dbFile:
        return process

    setattr(
        process,
        esSourceName,
        cms.ESSource(
            "PoolDBESSource",
            _CondDB.clone(connect=cms.string(_sqlite_connect(dbFile))),
            toGet=cms.VPSet(
                cms.PSet(
                    record=cms.string("JetCorrectionsRecord"),
                    tag=cms.string(jecTag or _default_jec_tag(jecPayload)),
                    label=cms.untracked.string(jecPayload),
                )
            ),
        ),
    )
    setattr(process, esSourceName + "Prefer", cms.ESPrefer("PoolDBESSource", esSourceName))
    return process


def makePicoPuppiProducer(
    candName="packedPFCandidates",
    vertexName="offlineSlimmedPrimaryVertices",
):
    from CommonTools.PileupAlgos.Puppi_cff import puppi

    return puppi.clone(
        candName=_as_input_tag(candName),
        vertexName=_as_input_tag(vertexName),
        clonePackedCands=cms.bool(True),
        useExistingWeights=cms.bool(True),
    )
# cms.EDProducer(
#     "PuppiProducer",
#     DeltaZCut=cms.double(0.1),
#     DeltaZCutForChargedFromPUVtxs=cms.double(0.2),
#     EtaMaxCharged=cms.double(99999),
#     EtaMaxPhotons=cms.double(2.5),
#     EtaMinUseDeltaZ=cms.double(4.0),
#     MinPuppiWeight=cms.double(0.01),
#     NumOfPUVtxsForCharged=cms.uint32(2),
#     PUProxyValue=cms.InputTag(""),
#     PtMaxCharged=cms.double(20.0),
#     PtMaxNeutrals=cms.double(200),
#     PtMaxNeutralsStartSlope=cms.double(20.0),
#     PtMaxPhotons=cms.double(-1),
#     UseDeltaZCut=cms.bool(True),
#     UseDeltaZCutForPileup=cms.bool(False),
#     UseFromPVLooseTight=cms.bool(False),
#     algos=cms.VPSet(
#         cms.PSet(
#             etaMin=cms.vdouble(0.0, 2.5),
#             etaMax=cms.vdouble(2.5, 3.5),
#             ptMin=cms.vdouble(0.0, 0.0),
#             MinNeutralPt=cms.vdouble(0.2, 0.2), 
#             MinNeutralPtSlope=cms.vdouble(0.015, 0.030),
#             RMSEtaSF=cms.vdouble(1.0, 1.0),
#             MedEtaSF=cms.vdouble(1.0, 1.0),
#             EtaMaxExtrap=cms.double(2.0),
#             puppiAlgos=cms.VPSet(
#                 cms.PSet(
#                     algoId=cms.int32(5),
#                     applyLowPUCorr=cms.bool(True),
#                     combOpt=cms.int32(0),
#                     cone=cms.double(0.4),
#                     rmsPtMin=cms.double(0.1),
#                     rmsScaleFactor=cms.double(1.0),
#                     useCharged=cms.bool(True),
#                 )
#             ),
#         ),
#         cms.PSet(
#             etaMin=cms.vdouble(3.5),
#             etaMax=cms.vdouble(10.0),
#             ptMin=cms.vdouble(0.0),
#             MinNeutralPt=cms.vdouble(2.0),
#             MinNeutralPtSlope=cms.vdouble(0.08),
#             RMSEtaSF=cms.vdouble(1.0),
#             MedEtaSF=cms.vdouble(0.75),
#             EtaMaxExtrap=cms.double(2.0),
#             puppiAlgos=cms.VPSet(
#                 cms.PSet(
#                     algoId=cms.int32(5),
#                     applyLowPUCorr=cms.bool(True),
#                     combOpt=cms.int32(0),
#                     cone=cms.double(0.4),
#                     rmsPtMin=cms.double(0.5),
#                     rmsScaleFactor=cms.double(1.0),
#                     useCharged=cms.bool(False),
#                 )
#             ),
#         ),
#     ),
#     applyCHS=cms.bool(True),
#     candName=_as_input_tag(candName),
#     clonePackedCands=cms.bool(False),
#     invertPuppi=cms.bool(False),
#     mightGet=cms.optional.untracked.vstring,
#     puppiDiagnostics=cms.bool(False),
#     puppiNoLep=cms.bool(False),
#     useExistingWeights=cms.bool(False),
#     useExp=cms.bool(False),
#     usePUProxyValue=cms.bool(False),
#     useVertexAssociation=cms.bool(False),
#     vertexAssociation=cms.InputTag(""),
#     vertexAssociationQuality=cms.int32(0),
#     vertexName=_as_input_tag(vertexName),
#     vtxNdofCut=cms.int32(4),
#     vtxZCut=cms.double(24),
# )


def addPuppiPFJets(process, candName, vertexName):
    """Rerun PUPPI and recluster AK4 PF PUPPI jets."""

    from RecoJets.JetProducers.ak4PFJets_cfi import ak4PFJetsPuppi as _ak4PFJetsPuppi

    process.offlinePFPuppi = makePicoPuppiProducer(candName=candName, vertexName=vertexName)
    process.offlineAK4PFPuppiJets = _ak4PFJetsPuppi.clone(
        src=cms.InputTag("offlinePFPuppi"),
        applyWeight=cms.bool(False),
        # Keep all jets produced by FastJet.
        # ak4PFJets inherits jetPtMin = 5 GeV by default.
        jetPtMin=cms.double(1.0),
    )

    if not hasattr(process, "reco2picoJetTask"):
        process.reco2picoJetTask = cms.Task()

    process.reco2picoJetTask.add(process.offlinePFPuppi)
    process.reco2picoJetTask.add(process.offlineAK4PFPuppiJets)
    return process, "offlineAK4PFPuppiJets"


def updateExistingPuppiPatJets(
    process,
    jetSource,
    labelName="Reco2PicoPuppi",
    jecPayload="AK4PFPuppi",
    jecLevels=("L1FastJet", "L2Relative", "L3Absolute"),
    pfCandidates="packedPFCandidates",
    pvSource="offlineSlimmedPrimaryVertices",
    svSource="slimmedSecondaryVertices",
):
    """Re-correct an existing MiniAOD PAT jet collection.

    This mode is intended for inputs such as `slimmedJetsPuppi`. It produces
    `selectedUpdatedPatJets<labelName>`.
    """

    from PhysicsTools.PatAlgos.tools.jetTools import updateJetCollection

    updateJetCollection(
        process,
        labelName=labelName,
        jetSource=_as_input_tag(jetSource),
        pfCandidates=_as_input_tag(pfCandidates),
        pvSource=_as_input_tag(pvSource),
        svSource=_as_input_tag(svSource),
        jetCorrections=(jecPayload, _jec_levels(jecLevels), "None"),
        #btagDiscriminators=[],
        #btagInfos=[],
        #printWarning=False,
    )

    return process, "selectedUpdatedPatJets%s" % labelName


def addPatJetsFromPuppiPFJets(
    process,
    jetSource,
    labelName="Reco2PicoPuppi",
    jecPayload="AK4PFPuppi",
    jecLevels=("L1FastJet", "L2Relative", "L3Absolute"),
    pfCandidates="packedPFCandidates",
    pvSource="offlineSlimmedPrimaryVertices",
    svSource="slimmedSecondaryVertices",
):
    """Create a new PAT jet collection from reclustered AK4 PF PUPPI jets.

    This mode is intended for `offlineAK4PFPuppiJets`. It uses
    `addJetCollection` rather than `updateJetCollection`, because the source is
    a reco PFJet collection, not an existing MiniAOD PAT jet collection.
    """

    from PhysicsTools.PatAlgos.tools.jetTools import addJetCollection

    addJetCollection(
        process,
        labelName=labelName,
        jetSource=_as_input_tag(jetSource),
        algo="AK",
        rParam=0.4,
        pfCandidates=_as_input_tag(pfCandidates),
        pvSource=_as_input_tag(pvSource),
        svSource=_as_input_tag(svSource),
        jetCorrections=(jecPayload, _jec_levels(jecLevels), "None"),
        # btagDiscriminators=None,
        # btagInfos=None,
        getJetMCFlavour=False,
        outputModules=[],
    )
    
    # Disable GEN matching for these newly-created PAT jets
    patJetsName = "patJets%s" % labelName

    if hasattr(process, patJetsName):
        patJets = getattr(process, patJetsName)

        patJets.addGenPartonMatch = False
        patJets.embedGenPartonMatch = False
        patJets.genPartonMatch = cms.InputTag("")

        patJets.addGenJetMatch = False
        patJets.embedGenJetMatch = False
        patJets.genJetMatch = cms.InputTag("")
    
    return process, "selectedPatJets%s" % labelName


def setupPuppiPatJetsForPico(
    process,
    rerunPUPPI=False,
    reApplyJEC=False,
    jetSource="slimmedJetsPuppi",
    candName="packedPFCandidates",
    vertexName="offlineSlimmedPrimaryVertices",
    pfCandidates="packedPFCandidates",
    svSource="slimmedSecondaryVertices",
    jecPayload="AK4PFPuppi",
    jecLevels=("L1FastJet", "L2Relative", "L3Absolute", "L2L3Residual"),
    jecDBFile="",
    jecDBTag="",
    labelName="Reco2PicoPuppi",
):
    """Configure optional PUPPI/JEC steps and return the PAT jet source for Pico.

    If neither `rerunPUPPI` nor `reApplyJEC` is enabled, the input `jetSource`
    is returned unchanged.
    """

    if not rerunPUPPI and not reApplyJEC:
        return process, jetSource

    process = addLocalJECDB(
        process,
        dbFile=jecDBFile,
        jecPayload=jecPayload,
        jecTag=jecDBTag,
    )

    if rerunPUPPI:
        process, pf_jet_source = addPuppiPFJets(
            process,
            candName=candName,
            vertexName=vertexName,
        )
        return addPatJetsFromPuppiPFJets(
            process,
            jetSource=pf_jet_source,
            labelName=labelName,
            jecPayload=jecPayload,
            jecLevels=jecLevels,
            pfCandidates=pfCandidates,
            pvSource=vertexName,
            svSource=svSource,
        )

    return updateExistingPuppiPatJets(
        process,
        jetSource=jetSource,
        labelName=labelName,
        jecPayload=jecPayload,
        jecLevels=jecLevels,
        pfCandidates=pfCandidates,
        pvSource=vertexName,
        svSource=svSource,
    )

