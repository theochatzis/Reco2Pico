import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *


def vertexTables(process, pvSrc="offlineSlimmedPrimaryVertices", pfcSrc="packedPFCandidates"):
    process.picoVertexTable = cms.EDProducer(
        "PicoVertexTableProducer",
        pvSrc=cms.InputTag(pvSrc),
        pfcSrc=cms.InputTag(pfcSrc),
        pvName=cms.string("PV"),
        goodPvCut=cms.string("!isFake && ndof > 4 && abs(z) <= 24 && position.Rho <= 2"),
        variables=cms.PSet(
            chi2=Var("chi2", float, doc="main primary vertex reduced chi2", precision=4),
            ndof=Var("ndof", float, doc="main primary vertex number of degree of freedom", precision=4),
            npvs=Var("npvs", "uint8", doc="total number of reconstructed primary vertices"),
            npvsGood=Var(
                "npvsGood",
                "uint8",
                doc="number of good reconstructed primary vertices. selection: !isFake && ndof > 4 && abs(z) <= 24 && position.Rho <= 2",
            ),
            score=Var("score", float, doc="main primary vertex score, i.e. sum pt2 of clustered objects", precision=4),
            sumpt2=Var("sumpt2", float, doc="sum pt2 of pf charged candidates for the main primary vertex", precision=4),
            sumpx=Var("sumpx", float, doc="sum px of pf charged candidates for the main primary vertex", precision=4),
            sumpy=Var("sumpy", float, doc="sum py of pf charged candidates for the main primary vertex", precision=4),
            x=Var("x", float, doc="main primary vertex position x coordinate", precision=6),
            y=Var("y", float, doc="main primary vertex position y coordinate", precision=6),
            z=Var("z", float, doc="main primary vertex position z coordinate", precision=6),
        ),
    )

    process.picoVertexTableTask = cms.Task(process.picoVertexTable)
    process.picoVertexTableSeq = cms.Sequence(process.picoVertexTableTask)

    return process