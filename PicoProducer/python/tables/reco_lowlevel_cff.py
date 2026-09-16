import FWCore.ParameterSet.Config as cms

from Reco2Pico.PicoProducer.tables.pfcands_reco_cff import recoPFCandidateTables
from Reco2Pico.PicoProducer.tables.tracks_cff import trackTables
from Reco2Pico.PicoProducer.tables.vertices_reco_cff import recoVertexTables
from Reco2Pico.PicoProducer.tables.pfclusters_cff import pfClusterTables
from Reco2Pico.PicoProducer.tables.rechits_cff import recHitTables


def recoLowLevelTables(
    process,
    inputTier="RECO",
    tables=("pfcands", "tracks", "vertices"),
    pfCandMinPt=0.0,
    trackMinPt=0.0,
    pfClusterMinEnergy=0.0,
    recHitMinAbsEnergy=0.0,
):
    """Assemble optional AOD/RECO low-level Pico tables into one Task."""
    requested = set(tables)
    modules = []

    if "vertices" in requested:
        modules.append(recoVertexTables(process))

    if "tracks" in requested:
        modules.append(trackTables(process, minPt=trackMinPt))

    if "pfcands" in requested:
        modules.append(
            recoPFCandidateTables(
                process,
                minPt=pfCandMinPt,
                trackTableMinPt=trackMinPt,
            )
        )

    if "pfclusters" in requested:
        if inputTier.upper() != "RECO":
            raise ValueError(
                "Standard AOD does not keep reco::PFCluster collections; "
                "enable pfclusters only for RECO or a custom AOD that keeps them."
            )
        modules.extend(pfClusterTables(process, minEnergy=pfClusterMinEnergy))

    if "rechits" in requested:
        modules.extend(
            recHitTables(
                process,
                inputTier=inputTier,
                minAbsEnergy=recHitMinAbsEnergy,
            )
        )

    process.picoRecoLowLevelTask = cms.Task(*modules)
    return process.picoRecoLowLevelTask
