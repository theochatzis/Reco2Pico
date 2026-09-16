import FWCore.ParameterSet.Config as cms


def trackTables(
    process,
    src="generalTracks",
    vertices="offlinePrimaryVertices",
    minPt=0.0,
):
    process.picoTrackTable = cms.EDProducer(
        "PicoTrackTableProducer",
        src=cms.InputTag(src),
        vertices=cms.InputTag(vertices),
        name=cms.string("Track"),
        minPt=cms.double(minPt),
    )
    return process.picoTrackTable
