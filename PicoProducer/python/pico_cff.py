import FWCore.ParameterSet.Config as cms

def _parse_enabled_tables(enabled_tables, isMC):
    if enabled_tables is None:
        tablesList_ = [
            "event",
            "pfRhoStrip",
            "vertices",
            "muons",
            "electrons",
            "jets",
            "met",
            "pfcands",
            "user_jets",
            "custom_objects",
        ]
         
        # if isMC:
        #     tablesList_.append("genJets")
        
        return tablesList_

    if isinstance(enabled_tables, str):
        return [x.strip() for x in enabled_tables.split(",") if x.strip()]

    return list(enabled_tables)


def buildPicoSequence(process,
        enabled_tables=None,
        isMC=True,
        jetSrc="slimmedJetsPuppi",
        pvSrc="offlineSlimmedPrimaryVertices",
        pfcSrc="packedPFCandidates",
        muSrc="slimmedMuons",
        metSrc="slimmedMETsPuppi",
        elSrc="slimmedElectrons"
    ):
    
    enabled_tables = _parse_enabled_tables(enabled_tables, isMC)

    process.picoTask = cms.Task()

    if "event" in enabled_tables:
        print("Adding Event Table")
        from Reco2Pico.PicoProducer.tables.event_cff import eventTables

        process = eventTables(process, isMC)
        process.picoTask.add(process.picoEventTableTask)
    
    # if "genJets" in enabled_tables and isMC:
    #     print("Adding genJets Table")
    #     from Reco2Pico.PicoProducer.tables.genJets_cff import genJetTables

    #     process = genJetTables(process)
    #     process.picoTask.add(process.picoGenJetTableTask)

    if "vertices" in enabled_tables:
        print("Adding vertices Table")
        from Reco2Pico.PicoProducer.tables.vertices_cff import vertexTables

        process = vertexTables(process, pvSrc=pvSrc, pfcSrc=pfcSrc)

        process.picoTask.add(process.picoVertexTableTask)
    
    if "pfRhoStrip" in enabled_tables:
        print("Adding pfRhoStrip Table")
        from Reco2Pico.PicoProducer.tables.pfRhoStripTable_cff import pfRhoStripTables

        process = pfRhoStripTables(process, pfcSrc=pfcSrc)

        process.picoTask.add(process.pfRhoStripTableTask)

    if "muons" in enabled_tables:
        print("Adding muons Table")
        from Reco2Pico.PicoProducer.tables.muons_cff import muonTables

        process = muonTables(process, src=muSrc)
        process.picoTask.add(process.picoMuonTableTask)

    if "electrons" in enabled_tables:
        print("Adding electrons Table")
        from Reco2Pico.PicoProducer.tables.electrons_cff import electronTables

        process = electronTables(process, src=elSrc)

        process.picoTask.add(process.picoElectronTableTask)

    if "jets" in enabled_tables:
        print("Adding jets Table")
        from Reco2Pico.PicoProducer.tables.jets_cff import jetTables

        process = jetTables(process, src=jetSrc, isMC=isMC, genJetSrc="slimmedGenJets")
        process.picoTask.add(process.picoJetTableTask)

    if "met" in enabled_tables:
        print("Adding met Table")
        from Reco2Pico.PicoProducer.tables.met_cff import metTables

        process = metTables(process, src=metSrc)
        process.picoTask.add(process.picoMETTableTask)
    
    if "pfcands" in enabled_tables:
        print("Adding pfcands Table")
        from Reco2Pico.PicoProducer.tables.pfcands_cff import pfCandidateTables

        process = pfCandidateTables(process, src=pfcSrc)
        process.picoTask.add(process.picoPFCandTableTask)

    if "user_jets" in enabled_tables:
        print("Adding user_jets Table")
        from Reco2Pico.PicoProducer.objects.user_jets_cff import userJets
        from Reco2Pico.PicoProducer.tables.user_jets_cff import userJetTables

        process, userJetCollection = userJets(process)
        process = userJetTables(process, src=userJetCollection)

        process.picoTask.add(process.userJetsTask)
        process.picoTask.add(process.picoUserJetTableTask)
    
    if "custom_objects" in enabled_tables:
        print("Adding custom_objects Table")
        from Reco2Pico.PicoProducer.tables.custom_objects_cff import customObjectTables

        process = customObjectTables(process)
        process.picoTask.add(process.picoCustomObjectTask)

    process.picoSequence = cms.Sequence(process.picoTask)

    return process.picoSequence