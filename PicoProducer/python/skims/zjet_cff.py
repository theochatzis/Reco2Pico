import FWCore.ParameterSet.Config as cms

from HLTrigger.HLTfilters.hltHighLevel_cfi import hltHighLevel
from PhysicsTools.PatAlgos.cleaningLayer1.jetCleaner_cfi import cleanPatJets



def setup(process, isMC=False):
    """
    Z+jet skim for MiniAOD.

    Selection:
      - pass muon HLT
      - pass MET filters
      - >= 2 isolated offline muons
      - >= 2 OS dimuon with 60 < m_mumu < 120 GeV
      - jets cleaned from selected isolated muons
      - >= 1 cleaned jet
      - deltaPhi(Z, jet) > 2.7 for at least one Z-jet pair
    """
    
    

    # ------------------------------------------------------------
    # Trigger selection
    # ------------------------------------------------------------
    process.zjetHLT = hltHighLevel.clone(
        TriggerResultsTag=cms.InputTag("TriggerResults", "", "HLT"),
        HLTPaths=cms.vstring(
            "HLT_IsoMu24_v*",
            "HLT_Mu50_v*",
            "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass8_v*",
        ),
        andOr=cms.bool(True),
        throw=cms.bool(False),
    )

    # ------------------------------------------------------------
    # MET filters
    #
    # In MiniAOD these are usually stored in TriggerResults::PAT.
    # Check with:
    #
    #   edmDumpEventContent file.root | grep TriggerResults
    #
    # If your file has TriggerResults::RECO instead, change "PAT" to "RECO".
    # ------------------------------------------------------------
    metFilterNames = [
        "Flag_goodVertices",
        "Flag_globalSuperTightHalo2016Filter",
        "Flag_HBHENoiseFilter",
        "Flag_HBHENoiseIsoFilter",
        "Flag_EcalDeadCellTriggerPrimitiveFilter",
        "Flag_BadPFMuonFilter",
        "Flag_BadPFMuonDzFilter",
        "Flag_hfNoisyHitsFilter",
    ]

    # Usually data-only. Keep it out of MC unless you know it exists.
    if not isMC:
        metFilterNames += [
            "Flag_eeBadScFilter",
        ]

    process.zjetMETFilters = hltHighLevel.clone(
        TriggerResultsTag=cms.InputTag("TriggerResults", "", "PAT"),
        HLTPaths=cms.vstring(*metFilterNames),
        andOr=cms.bool(False),   # require all listed MET filters
        throw=cms.bool(False),   # set True once you verified all flags exist
    )

    # ------------------------------------------------------------
    # Isolated muons
    #
    # This is intentionally a simple skim-level isolation.
    # Tighten/replace with your preferred analysis ID later.
    # ------------------------------------------------------------
    
    # from Reco2Pico.PicoProducer.objects.userMuons_cff import userMuons
    # process, zjetMuons = userMuons(process)

    process.zjetMuons = cms.EDFilter(
        "PATMuonSelector",
        src=cms.InputTag("slimmedMuons"),
        cut=cms.string(
        "pt > 10. && abs(eta) < 2.4 && "
        "isPFMuon && "
        "(isGlobalMuon || isTrackerMuon) && "
        "(pfIsolationR04().sumChargedHadronPt"
        " + max(0., pfIsolationR04().sumNeutralHadronEt"
        " + pfIsolationR04().sumPhotonEt"
        " - 0.5*pfIsolationR04().sumPUPt))/pt < 0.15"
        ),
        filter=cms.bool(False),
    )

    process.zjetTwoMuons = cms.EDFilter(
        "CandViewCountFilter",
        src=cms.InputTag("zjetMuons"),
        minNumber=cms.uint32(2),
    )

    # ------------------------------------------------------------
    # Opposite-sign dimuon Z candidate
    # ------------------------------------------------------------
    process.zjetDimuons = cms.EDProducer(
        "CandViewShallowCloneCombiner",
        decay=cms.string("zjetMuons@+ zjetMuons@-"),
        cut=cms.string("70 < mass < 110"),
    )

    process.zjetOneDimuon = cms.EDFilter(
        "CandViewCountFilter",
        src=cms.InputTag("zjetDimuons"),
        minNumber=cms.uint32(1),
    )

    # ------------------------------------------------------------
    # Clean jets from isolated muons
    #
    # Removes jets within deltaR < 0.4 of selected zjetMuons.
    # ------------------------------------------------------------
    process.zjetCleanedJets = cleanPatJets.clone(
        src=cms.InputTag("slimmedJets"),
        preselection=cms.string(""),
        checkOverlaps=cms.PSet(
            muons=cms.PSet(
                src=cms.InputTag("zjetMuons"),
                algorithm=cms.string("byDeltaR"),
                preselection=cms.string(""),
                deltaR=cms.double(0.4),
                checkRecoComponents=cms.bool(False),
                pairCut=cms.string(""),
                requireNoOverlaps=cms.bool(True),
            )
        ),
        finalCut=cms.string(""),
    )

    process.zjetJets = cms.EDFilter(
        "PATJetSelector",
        src=cms.InputTag("zjetCleanedJets"),
        cut=cms.string(
            "pt > 15 && abs(eta) < 5.0"
        ),
        filter=cms.bool(False),
    )

    process.zjetOneJet = cms.EDFilter(
        "CandViewCountFilter",
        src=cms.InputTag("zjetJets"),
        minNumber=cms.uint32(1),
    )

    # ------------------------------------------------------------
    # Delta phi between Z and cleaned jet
    #
    # Requires at least one Z-jet pair with |deltaPhi| > 2.7.
    # This uses the custom EDFilter below.
    # ------------------------------------------------------------
    process.zjetDeltaPhi = cms.EDFilter(
        "JetRefDeltaPhiFilter",
        refSrc=cms.InputTag("zjetDimuons"),
        jetSrc=cms.InputTag("zjetJets"),
        minDeltaPhi=cms.double(2.7),
    )

    process.zjetSkimSequence = cms.Sequence(
        #process.userMuonsSequence *
        process.zjetHLT *
        #process.zjetMETFilters *
        process.zjetMuons *
        process.zjetTwoMuons *
        process.zjetDimuons *
        process.zjetOneDimuon *
        process.zjetCleanedJets *
        process.zjetJets *
        process.zjetOneJet *
        process.zjetDeltaPhi
    )

    return process.zjetSkimSequence