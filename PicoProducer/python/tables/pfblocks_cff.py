import FWCore.ParameterSet.Config as cms

from Reco2Pico.PicoProducer.tables.pfclusters_cff import DEFAULT_PFCLUSTERS

# PFCluster table codes used by PFBlockElem_clusterTable (0 = no cluster).
PFCLUSTER_TABLE_CODES = {"ECAL": 1, "HCAL": 2, "HO": 3, "HF": 4, "PS": 5}


def pfBlockTables(
    process,
    blocks="particleFlowBlock",
    candidates="particleFlow",
    tracks="generalTracks",
    gsfTracks="electronGsfTracks",
    muons="muons",
    clusterSources=None,
    candMinPt=0.0,
    trackTableMinPt=0.0,
    pfClusterMinEnergy=0.0,
    writeLinks=True,
):
    """PFBlockElem / PFBlockLink / PFCandElem tables (RECO only).

    The row indices written by the producer refer to the Pico tables of the
    same job, so the thresholds must be the ones used for the PFCand, Track and
    PFCluster<X> tables (``pfCandMinPt``, ``trackMinPt``, ``pfClusterMinEnergy``
    of the RECO workflow).
    """
    clusterSources = DEFAULT_PFCLUSTERS if clusterSources is None else clusterSources
    clusters = cms.VPSet()
    for suffix, src in clusterSources.items():
        clusters.append(
            cms.PSet(
                src=cms.InputTag(src),
                code=cms.int32(PFCLUSTER_TABLE_CODES[suffix]),
                table=cms.string("PFCluster%s" % suffix),
            )
        )

    process.picoPFBlockTable = cms.EDProducer(
        "PicoPFBlockTableProducer",
        blocks=cms.InputTag(blocks),
        candidates=cms.InputTag(candidates),
        tracks=cms.InputTag(tracks),
        gsfTracks=cms.InputTag(gsfTracks),
        muons=cms.InputTag(muons),
        clusters=clusters,
        name=cms.string("PFBlock"),
        candElementsName=cms.string("PFCandElem"),
        candMinPt=cms.double(candMinPt),
        trackTableMinPt=cms.double(trackTableMinPt),
        clusterMinEnergy=cms.double(pfClusterMinEnergy),
        writeLinks=cms.bool(writeLinks),
    )
    return process.picoPFBlockTable
