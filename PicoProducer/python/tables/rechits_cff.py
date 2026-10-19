import FWCore.ParameterSet.Config as cms


def recHitTables(process, inputTier="RECO", minAbsEnergy=0.0, fullEcalRecHits=False):
    """Create ECAL and HCAL RecHit tables.

    RECO uses the full HCAL RecHit collections. AOD uses reduced HCAL RecHits.
    ECAL reduced RecHits (the cells around the interesting objects) are retained in
    both AOD and RECO event content; with fullEcalRecHits (RECO only) the tables take
    every ECAL rechit instead (ecalRecHit), as a per-cell study against the sim
    deposits needs.
    """
    tier = inputTier.upper()
    if tier not in ("AOD", "RECO"):
        raise ValueError("inputTier must be 'AOD' or 'RECO'")
    if fullEcalRecHits and tier != "RECO":
        raise ValueError("fullEcalRecHits needs the RECO tier")
    eb = cms.InputTag("ecalRecHit", "EcalRecHitsEB") if fullEcalRecHits else cms.InputTag("reducedEcalRecHitsEB")
    ee = cms.InputTag("ecalRecHit", "EcalRecHitsEE") if fullEcalRecHits else cms.InputTag("reducedEcalRecHitsEE")

    process.picoEBRecHitTable = cms.EDProducer(
        "PicoEcalRecHitTableProducer",
        src=eb,
        name=cms.string("EBRecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )
    process.picoEERecHitTable = cms.EDProducer(
        "PicoEcalRecHitTableProducer",
        src=ee,
        name=cms.string("EERecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )

    if tier == "RECO":
        hbhe = cms.InputTag("hbhereco")
        hf = cms.InputTag("hfreco")
        ho = cms.InputTag("horeco")
    else:
        hbhe = cms.InputTag("reducedHcalRecHits", "hbhereco")
        hf = cms.InputTag("reducedHcalRecHits", "hfreco")
        ho = cms.InputTag("reducedHcalRecHits", "horeco")

    process.picoHBHERecHitTable = cms.EDProducer(
        "PicoHBHERecHitTableProducer",
        src=hbhe,
        name=cms.string("HBHERecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )
    process.picoHFRecHitTable = cms.EDProducer(
        "PicoHFRecHitTableProducer",
        src=hf,
        name=cms.string("HFRecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )
    process.picoHORecHitTable = cms.EDProducer(
        "PicoHORecHitTableProducer",
        src=ho,
        name=cms.string("HORecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )

    return [
        process.picoEBRecHitTable,
        process.picoEERecHitTable,
        process.picoHBHERecHitTable,
        process.picoHFRecHitTable,
        process.picoHORecHitTable,
    ]
