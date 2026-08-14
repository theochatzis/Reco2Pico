import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.common_cff import Var
from PhysicsTools.NanoAOD.simplePATCandidateFlatTableProducer_cfi import (
    simplePATCandidateFlatTableProducer,
)


def pfCandidateTables(process, src="packedPFCandidates"):
    process.picoPFCandTable = simplePATCandidateFlatTableProducer.clone(
        src=cms.InputTag(src),
        cut=cms.string("pt > 0.0 && abs(eta) < 5.0"),
        name=cms.string("PFCand"),
        doc=cms.string("selected packed PF candidates for PicoAOD"),
        singleton=cms.bool(False),
        extension=cms.bool(False),

        externalVariables=cms.PSet(),

        variables=cms.PSet(
            # --------------------------------------------------
            # Basic candidate quantities
            # --------------------------------------------------
            pt = Var(
                "pt",
                float,
                precision=6,
                doc="Unweighted PF candidate pT"
            ),

            eta = Var(
                "eta",
                float,
                precision=6,
                doc="PF candidate eta"
            ),

            phi = Var(
                "phi",
                float,
                precision=6,
                doc="PF candidate phi"
            ),

            mass = Var(
                "mass",
                float,
                precision=6,
                doc="PF candidate mass"
            ),

            energy = Var(
                "energy",
                float,
                precision=6,
                doc="PF candidate energy"
            ),

            pdgId = Var(
                "pdgId",
                int,
                doc="PF candidate PDG/PF type"
            ),

            charge = Var(
                "charge",
                int,
                doc="PF candidate electric charge"
            ),


            # --------------------------------------------------
            # Track / vertex information
            # --------------------------------------------------
            ptTrk = Var(
                "ptTrk()",
                float,
                precision=6,
                doc="Track transverse momentum stored in PackedCandidate"
            ),

            fromPV = Var(
                "fromPV()",
                int,
                doc="PackedCandidate PV association"
            ),

            dz = Var(
                "dz()",
                float,
                precision=6,
                doc="dz relative to associated PV"
            ),

            dxy = Var(
                "dxy()",
                float,
                precision=6,
                doc="dxy relative to associated PV"
            ),


            # --------------------------------------------------
            # Existing PUPPI information
            # --------------------------------------------------
            puppiWeight = Var(
                "puppiWeight()",
                float,
                precision=6,
                doc="Existing PUPPI weight"
            ),

            puppiWeightNoLep = Var(
                "puppiWeightNoLep()",
                float,
                precision=6,
                doc="Existing no-lepton PUPPI weight"
            ),


            # --------------------------------------------------
            # Calorimeter fractions stored in MiniAOD
            # --------------------------------------------------
            caloFraction = Var(
                "caloFraction()",
                float,
                precision=6,
                doc="(ECAL+HCAL energy)/candidate energy"
            ),

            hcalFraction = Var(
                "hcalFraction()",
                float,
                precision=6,
                doc="HCAL fraction of calorimeter energy"
            ),

            rawCaloFraction = Var(
                "rawCaloFraction()",
                float,
                precision=6,
                doc="Raw (ECAL+HCAL)/candidate energy for isolated charged hadrons"
            ),

            rawHcalFraction = Var(
                "rawHcalFraction()",
                float,
                precision=6,
                doc="Raw HCAL fraction for isolated charged hadrons"
            ),

            isIsolatedChargedHadron = Var(
                "isIsolatedChargedHadron()",
                bool,
                doc="MiniAOD isolated charged-hadron flag"
            ),


            # --------------------------------------------------
            # Convenient derived calorimeter energies
            # --------------------------------------------------
            caloEnergy = Var(
                "energy*caloFraction()",
                float,
                precision=6,
                doc="Stored ECAL+HCAL energy"
            ),

            hcalEnergy = Var(
                "energy*caloFraction()*hcalFraction()",
                float,
                precision=6,
                doc="Stored HCAL energy"
            ),

            ecalEnergy = Var(
                "energy*caloFraction()*(1-hcalFraction())",
                float,
                precision=6,
                doc="Stored ECAL energy"
            ),

            rawCaloEnergy = Var(
                "energy*rawCaloFraction()",
                float,
                precision=6,
                doc="Raw ECAL+HCAL energy for isolated charged hadrons"
            ),

            rawHcalEnergy = Var(
                "energy*rawCaloFraction()*rawHcalFraction()",
                float,
                precision=6,
                doc="Raw HCAL energy for isolated charged hadrons"
            ),

            rawEcalEnergy = Var(
                "energy*rawCaloFraction()*(1-rawHcalFraction())",
                float,
                precision=6,
                doc="Raw ECAL energy for isolated charged hadrons"
            ),
        ),
    )

    process.picoPFCandTableTask = cms.Task(process.picoPFCandTable)
    process.picoPFCandTableSeq = cms.Sequence(process.picoPFCandTableTask)

    return process
