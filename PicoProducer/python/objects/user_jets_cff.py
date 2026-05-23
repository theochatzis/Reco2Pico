import FWCore.ParameterSet.Config as cms


def userJets(process):
    """Minimal optional custom-jet object builder.

    This only selects slimmedJets. It is intentionally simple; add
    updateJetCollection/JEC/PFJetID steps here later once the basic Pico output
    is stable.
    """
    process.userJetsTask = cms.Task()

    from PhysicsTools.PatAlgos.selectionLayer1.jetSelector_cfi import selectedPatJets

    process.selectedUserJets = selectedPatJets.clone(
        src=cms.InputTag("slimmedJets"),
        cut=cms.string("pt > 30 && abs(eta) < 5.0"),
    )
    process.userJetsTask.add(process.selectedUserJets)
    process.userJetsSeq = cms.Sequence(process.userJetsTask)
    return process, "selectedUserJets"
