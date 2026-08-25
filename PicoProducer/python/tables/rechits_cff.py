import FWCore.ParameterSet.Config as cms


def recHitTables(process, inputTier="RECO", minAbsEnergy=0.0):
    """Create ECAL and HCAL RecHit tables.

    RECO uses the full HCAL RecHit collections. AOD uses reduced HCAL RecHits.
    ECAL reduced RecHits are retained in both AOD and RECO event content.
    """
    tier = inputTier.upper()
    if tier not in ("AOD", "RECO"):
        raise ValueError("inputTier must be 'AOD' or 'RECO'")

    process.picoEBRecHitTable = cms.EDProducer(
        "PicoEcalRecHitTableProducer",
        src=cms.InputTag("reducedEcalRecHitsEB"),
        name=cms.string("EBRecHit"),
        minAbsEnergy=cms.double(minAbsEnergy),
    )
    process.picoEERecHitTable = cms.EDProducer(
        "PicoEcalRecHitTableProducer",
        src=cms.InputTag("reducedEcalRecHitsEE"),
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
