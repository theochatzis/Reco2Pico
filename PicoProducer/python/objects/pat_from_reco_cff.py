import FWCore.ParameterSet.Config as cms


def makePatObjectsFromReco(
    process,
    isMC=True,
    makeJets=False,
    makeMuons=False,
    makeElectrons=False,
    jetSrc="ak4PFJetsPuppi",
    genJetSrc="ak4GenJetsNoNu",
    muonSrc="muons",
    electronSrc="gedGsfElectrons",
    pfCandSrc="particleFlow",
    vertexSrc="offlinePrimaryVertices",
    beamSpotSrc="offlineBeamSpot",
):
    """Build a deliberately minimal PAT compatibility layer from AOD/RECO.

    This is *not* a MiniAOD recreation.  It only creates pat::Jet, pat::Muon
    and pat::Electron collections so that the same Pico FlatTable producers
    used for MiniAOD can consume PAT interfaces.

    No b tagging, PNet, flavour matching, trigger matching, mini-isolation or
    electron VID is run here.
    """

    task = cms.Task()
    sources = {}

    if makeJets:
        from PhysicsTools.PatAlgos.recoLayer0.jetCorrFactors_cfi import patJetCorrFactors
        from PhysicsTools.PatAlgos.producersLayer1.jetProducer_cfi import patJets

        levels = ["L1FastJet", "L2Relative", "L3Absolute"]
        if not isMC:
            levels.append("L2L3Residual")

        process.picoPatJetCorrFactors = patJetCorrFactors.clone(
            src=cms.InputTag(jetSrc),
            payload=cms.string("AK4PFPuppi"),
            levels=cms.vstring(*levels),
            primaryVertices=cms.InputTag(vertexSrc),
            rho=cms.InputTag("fixedGridRhoFastjetAll"),
            useNPV=cms.bool(True),
            useRho=cms.bool(True),
        )

        #
        # Reco <-> GenJet matching
        #
        if isMC:
            from PhysicsTools.PatAlgos.mcMatchLayer0.jetMatch_cfi import patJetGenJetMatch

            process.picoPatJetGenJetMatch = patJetGenJetMatch.clone(
                src=cms.InputTag(jetSrc),
                matched=cms.InputTag(genJetSrc),
                maxDeltaR=cms.double(0.4),
                resolveAmbiguities=cms.bool(True),
                resolveByMatchQuality=cms.bool(False),
            )

            task.add(process.picoPatJetGenJetMatch)

        process.picoPatJets = patJets.clone(
            jetSource=cms.InputTag(jetSrc),

            embedPFCandidates=cms.bool(False),

            addJetCorrFactors=cms.bool(True),
            jetCorrFactorsSource=cms.VInputTag(
                cms.InputTag("picoPatJetCorrFactors")
            ),

            # No tagging
            addBTagInfo=cms.bool(False),
            addDiscriminators=cms.bool(False),
            discriminatorSources=cms.VInputTag(),
            addTagInfos=cms.bool(False),
            tagInfoSources=cms.VInputTag(),

            addAssociatedTracks=cms.bool(False),
            addJetCharge=cms.bool(False),

            #
            # GenJet matching
            #
            addGenJetMatch=cms.bool(isMC),
            embedGenJetMatch=cms.bool(isMC),
            genJetMatch=cms.InputTag("picoPatJetGenJetMatch"),

            #
            # Keep parton/flavour matching off for now.
            # This is independent of reco <-> GenJet matching.
            #
            addGenPartonMatch=cms.bool(False),
            embedGenPartonMatch=cms.bool(False),

            getJetMCFlavour=cms.bool(False),
            addJetFlavourInfo=cms.bool(False),
        )

        task.add(process.picoPatJetCorrFactors)
        task.add(process.picoPatJets)

        sources["jets"] = "picoPatJets"

    if isMC:
        sources["genjets"] = genJetSrc

    if makeMuons:
        from PhysicsTools.PatAlgos.producersLayer1.muonProducer_cfi import patMuons

        process.picoPatMuons = patMuons.clone(
            muonSource=cms.InputTag(muonSrc),
            useParticleFlow=cms.bool(False),
            pfMuonSource=cms.InputTag(pfCandSrc),
            embedMuonBestTrack=cms.bool(False),
            embedTunePMuonBestTrack=cms.bool(False),
            forceBestTrackEmbedding=cms.bool(False),
            embedTrack=cms.bool(False),
            embedCombinedMuon=cms.bool(False),
            embedStandAloneMuon=cms.bool(False),
            embedPickyMuon=cms.bool(False),
            embedTpfmsMuon=cms.bool(False),
            embedDytMuon=cms.bool(False),
            embedPFCandidate=cms.bool(False),
            embedCaloMETMuonCorrs=cms.bool(False),
            addInverseBeta=cms.bool(False),
            addGenMatch=cms.bool(False),
            embedGenMatch=cms.bool(False),
            embedHighLevelSelection=cms.bool(True),
            beamLineSrc=cms.InputTag(beamSpotSrc),
            pvSrc=cms.InputTag(vertexSrc),
            embedPfEcalEnergy=cms.bool(False),
            computeMiniIso=cms.bool(False),
            addPuppiIsolation=cms.bool(False),
            computePuppiCombinedIso=cms.bool(False),
            computeMuonIDMVA=cms.bool(False),
            recomputeBasicSelectors=cms.bool(True),
            useJec=cms.bool(False),
            computeSoftMuonMVA=cms.bool(False),
            addTriggerMatching=cms.bool(False),
        )

        task.add(process.picoPatMuons)
        sources["muons"] = "picoPatMuons"

    if makeElectrons:
        from PhysicsTools.PatAlgos.producersLayer1.electronProducer_cfi import patElectrons

        process.picoPatElectrons = patElectrons.clone(
            electronSource=cms.InputTag(electronSrc),
            pfElectronSource=cms.InputTag(pfCandSrc),
            addMVAVariables=cms.bool(False),
            embedGsfElectronCore=cms.bool(False),
            embedGsfTrack=cms.bool(False),
            embedSuperCluster=cms.bool(False),
            embedPflowSuperCluster=cms.bool(False),
            embedSeedCluster=cms.bool(False),
            embedBasicClusters=cms.bool(False),
            embedPreshowerClusters=cms.bool(False),
            embedPflowBasicClusters=cms.bool(False),
            embedPflowPreshowerClusters=cms.bool(False),
            embedPFCandidate=cms.bool(False),
            embedTrack=cms.bool(False),
            embedRecHits=cms.bool(False),
            addElectronID=cms.bool(False),
            addGenMatch=cms.bool(False),
            embedGenMatch=cms.bool(False),
            embedHighLevelSelection=cms.bool(True),
            beamLineSrc=cms.InputTag(beamSpotSrc),
            pvSrc=cms.InputTag(vertexSrc),
            addPFClusterIso=cms.bool(False),
            addPuppiIsolation=cms.bool(False),
            computeMiniIso=cms.bool(False),
        )

        task.add(process.picoPatElectrons)
        sources["electrons"] = "picoPatElectrons"

    process.picoPatFromRecoTask = task
    return process, sources
