import FWCore.ParameterSet.Config as cms


def _parse_enabled_tables(enabled_tables):
    if enabled_tables is None:
        return [
            "event",
            "vertices",
            "muons",
            "electrons",
            "jets",
            "met",
            "pfcands",
            "user_jets",
            "custom_objects",
        ]

    if isinstance(enabled_tables, str):
        return [x.strip() for x in enabled_tables.split(",") if x.strip()]

    return list(enabled_tables)


def buildPicoSequence(process, enabled_tables=None):
    enabled_tables = _parse_enabled_tables(enabled_tables)

    process.picoTask = cms.Task()

    if "event" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.event_cff import eventTables

        process = eventTables(process)
        process.picoTask.add(process.picoEventTableTask)
    
    if "vertices" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.vertices_cff import vertexTables

        process = vertexTables(process, pvSrc="offlineSlimmedPrimaryVertices", pfcSrc="packedPFCandidates")

        process.picoTask.add(process.picoVertexTableTask)

    if "muons" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.muons_cff import muonTables

        process = muonTables(process, src="slimmedMuons")
        process.picoTask.add(process.picoMuonTableTask)

    if "electrons" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.electrons_cff import electronTables

        process = electronTables(process, src="slimmedElectrons")

        process.picoTask.add(process.picoElectronTableTask)

    if "jets" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.jets_cff import jetTables

        process = jetTables(process, src="slimmedJetsPuppi")
        process.picoTask.add(process.picoJetTableTask)

    if "met" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.met_cff import metTables

        process = metTables(process, src="slimmedMETsPuppi")
        process.picoTask.add(process.picoMETTableTask)
    
    if "pfcands" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.pfcands_cff import pfCandidateTables

        process = pfCandidateTables(process, src="packedPFCandidates")
        process.picoTask.add(process.picoPFCandTableTask)

    if "user_jets" in enabled_tables:
        from Reco2Pico.PicoProducer.objects.user_jets_cff import userJets
        from Reco2Pico.PicoProducer.tables.user_jets_cff import userJetTables

        process, userJetCollection = userJets(process)
        process = userJetTables(process, src=userJetCollection)

        process.picoTask.add(process.userJetsTask)
        process.picoTask.add(process.picoUserJetTableTask)
    
    if "custom_objects" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.custom_objects_cff import customObjectTables

        process = customObjectTables(process)
        process.picoTask.add(process.picoCustomObjectTask)

    process.picoSequence = cms.Sequence(process.picoTask)

    return process.picoSequence