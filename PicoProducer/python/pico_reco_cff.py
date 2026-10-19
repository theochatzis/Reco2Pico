import FWCore.ParameterSet.Config as cms


SUPPORTED_TABLES = {
    "event",
    "muons",
    "electrons",
    "jets",
    "pfcands",
    "tracks",
    "vertices",
    "pfclusters",
    "rechits",
    "pfblocks",
    "genparts",
    "sim",
    "simcalo",
    "recojets",
}


def _parse_enabled_tables(enabled_tables):
    if enabled_tables is None:
        return ["event", "muons", "electrons", "jets", "pfcands", "tracks", "vertices"]
    if isinstance(enabled_tables, str):
        return [x.strip() for x in enabled_tables.split(",") if x.strip()]
    return list(enabled_tables)


def buildRecoPicoSequence(
    process,
    enabled_tables=None,
    isMC=True,
    inputTier="AOD",
    pfCandMinPt=0.0,
    trackMinPt=0.0,
    pfClusterMinEnergy=0.0,
    recHitMinAbsEnergy=0.0,
    tpPileupMinPt=1.0,
    simJetSelection="leaves",
    simJetMinPt=5.0,
    genJetMinPt=5.0,
    tpAssociation="chi2",
    ecalCellThreshold=0.0,
    hcalCellThreshold=0.0,
    simPFChargedMaxAbsEta=2.5,
    simPFChargedMinPt=0.5,
):
    """Build Pico tables from AOD or RECO.

    High-level jets/muons/electrons are first converted to a minimal PAT layer
    and then passed to the same table builders used for MiniAOD.

    Low-level reco objects are written directly to FlatTables.
    """
    tier = inputTier.upper()
    if tier not in ("AOD", "RECO"):
        raise ValueError("inputTier must be 'AOD' or 'RECO'")

    enabled_tables = _parse_enabled_tables(enabled_tables)
    unknown = sorted(set(enabled_tables) - SUPPORTED_TABLES)
    if unknown:
        raise ValueError(
            "Unsupported AOD/RECO Pico table group(s): %s. Supported groups: %s"
            % (", ".join(unknown), ", ".join(sorted(SUPPORTED_TABLES)))
        )

    if "pfclusters" in enabled_tables and tier != "RECO":
        raise ValueError("'pfclusters' is RECO-only for standard event content")
    if "pfblocks" in enabled_tables and tier != "RECO":
        raise ValueError("'pfblocks' is RECO-only: standard AOD does not keep reco::PFBlock")
    for group in ("genparts", "sim"):
        if group in enabled_tables and not isMC:
            raise ValueError("'%s' requires MC input" % group)
    if "sim" in enabled_tables and "genparts" not in enabled_tables:
        raise ValueError("'sim' requires the 'genparts' group (GenPart indices)")
    if "simcalo" in enabled_tables and "sim" not in enabled_tables:
        raise ValueError("'simcalo' requires the 'sim' group")
    if "recojets" in enabled_tables and not {"sim", "pfcands"} <= set(enabled_tables):
        raise ValueError("'recojets' requires the 'sim' and 'pfcands' groups")

    process.picoRecoTask = cms.Task()

    makeJets = "jets" in enabled_tables
    makeMuons = "muons" in enabled_tables
    makeElectrons = "electrons" in enabled_tables

    if makeJets or makeMuons or makeElectrons:
        from Reco2Pico.PicoProducer.objects.pat_from_reco_cff import makePatObjectsFromReco

        process, patSources = makePatObjectsFromReco(
            process,
            isMC=isMC,
            makeJets=makeJets,
            makeMuons=makeMuons,
            makeElectrons=makeElectrons,
        )
        process.picoRecoTask.add(process.picoPatFromRecoTask)
    else:
        patSources = {}

    if "event" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.event_cff import eventTables

        process = eventTables(
            process,
            isMC=isMC,
            puSrc="addPileupInfo",
            pvSrc="offlinePrimaryVertices",
        )
        process.picoRecoTask.add(process.picoEventTableTask)

    if "muons" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.muons_cff import muonTables

        process = muonTables(process, src=patSources["muons"])
        process.picoRecoTask.add(process.picoMuonTableTask)

    if "electrons" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.electrons_cff import electronTables

        # The minimal PAT layer intentionally does not run VID.  Keep the same
        # table builder, but omit MiniAOD-only userInt electron IDs.
        process = electronTables(process, src=patSources["electrons"], includeIDs=False)
        process.picoRecoTask.add(process.picoElectronTableTask)

    if "jets" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.jets_cff import jetTables

        process = jetTables(process, src=patSources["jets"], isMC=isMC, genJetSrc="ak4GenJetsNoNu")
        process.picoRecoTask.add(process.picoJetTableTask)

    lowlevel = [
        x
        for x in ("pfcands", "tracks", "vertices", "pfclusters", "rechits")
        if x in enabled_tables
    ]
    if lowlevel:
        from Reco2Pico.PicoProducer.tables.reco_lowlevel_cff import recoLowLevelTables

        recoLowLevelTables(
            process,
            inputTier=tier,
            tables=lowlevel,
            pfCandMinPt=pfCandMinPt,
            trackMinPt=trackMinPt,
            pfClusterMinEnergy=pfClusterMinEnergy,
            recHitMinAbsEnergy=recHitMinAbsEnergy,
        )
        process.picoRecoTask.add(process.picoRecoLowLevelTask)

    if "pfblocks" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.pfblocks_cff import pfBlockTables

        process.picoRecoTask.add(
            pfBlockTables(
                process,
                candMinPt=pfCandMinPt,
                trackTableMinPt=trackMinPt,
                pfClusterMinEnergy=pfClusterMinEnergy,
            )
        )

    if "genparts" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.sim_cff import genParticleTables

        process.picoRecoTask.add(genParticleTables(process, genJetMinPt=genJetMinPt))

    if "sim" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.sim_cff import simTables

        process.picoRecoTask.add(
            simTables(
                process,
                trackTableMinPt=trackMinPt,
                tpPileupMinPt=tpPileupMinPt,
                simJetSelection=simJetSelection,
                simJetMinPt=simJetMinPt,
                tpAssociation=tpAssociation,
            )
        )

    if "simcalo" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.sim_cff import simCaloTables

        process.picoRecoTask.add(
            simCaloTables(
                process,
                simJetMinPt=simJetMinPt,
                ecalCellThreshold=ecalCellThreshold,
                hcalCellThreshold=hcalCellThreshold,
                chargedMaxAbsEta=simPFChargedMaxAbsEta,
                chargedMinPt=simPFChargedMinPt,
            )
        )

    if "recojets" in enabled_tables:
        from Reco2Pico.PicoProducer.tables.recojets_cff import recoJetTables

        process.picoRecoTask.add(recoJetTables(process, pfCandMinPt=pfCandMinPt, jetMinPt=simJetMinPt))

    process.picoSequence = cms.Sequence(process.picoRecoTask)
    return process.picoSequence
