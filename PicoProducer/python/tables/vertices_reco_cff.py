import FWCore.ParameterSet.Config as cms


def recoVertexTables(process, src="offlinePrimaryVertices"):
    process.picoRecoVertexTable = cms.EDProducer(
        "PicoRecoVertexTableProducer",
        src=cms.InputTag(src),
        name=cms.string("Vertex"),
    )
    return process.picoRecoVertexTable
