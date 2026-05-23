import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.common_cff import Var
from PhysicsTools.NanoAOD.simplePATCandidateFlatTableProducer_cfi import (
    simplePATCandidateFlatTableProducer,
)


def pfCandidateTables(process, src="packedPFCandidates"):
    process.picoPFCandTable = simplePATCandidateFlatTableProducer.clone(
        src=cms.InputTag(src),
        cut=cms.string("pt > 0.5 && abs(eta) < 2.5"),
        name=cms.string("PFCand"),
        doc=cms.string("selected packed PF candidates for PicoAOD"),
        singleton=cms.bool(False),
        extension=cms.bool(False),

        externalVariables=cms.PSet(),

        variables=cms.PSet(
            pt=Var("pt", float, doc="PF candidate pT", precision=6),
            eta=Var("eta", float, doc="PF candidate eta", precision=6),
            phi=Var("phi", float, doc="PF candidate phi", precision=6),
            mass=Var("mass", float, doc="PF candidate mass", precision=6),

            pdgId=Var("pdgId", int, doc="PF candidate PDG ID"),
            charge=Var("charge", int, doc="electric charge"),

            puppiWeight=Var(
                "puppiWeight()",
                float,
                doc="PUPPI weight",
                precision=6,
            ),

            fromPV=Var(
                "fromPV()",
                int,
                doc="packed candidate fromPV flag",
            ),
        ),
    )

    process.picoPFCandTableTask = cms.Task(process.picoPFCandTable)
    process.picoPFCandTableSeq = cms.Sequence(process.picoPFCandTableTask)

    return process
