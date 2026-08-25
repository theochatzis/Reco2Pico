import FWCore.ParameterSet.Config as cms


def recoPFCandidateTables(
    process,
    src="particleFlow",
    tracks="generalTracks",
    vertices="offlinePrimaryVertices",
    minPt=0.0,
    trackTableMinPt=0.0,
):
    process.picoRecoPFCandidateTable = cms.EDProducer(
        "PicoRecoPFCandidateTableProducer",
        src=cms.InputTag(src),
        tracks=cms.InputTag(tracks),
        vertices=cms.InputTag(vertices),
        name=cms.string("PFCand"),
        minPt=cms.double(minPt),
        trackTableMinPt=cms.double(trackTableMinPt),
    )
    return process.picoRecoPFCandidateTable
