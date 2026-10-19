import FWCore.ParameterSet.Config as cms


def caloDigiTables(process, rawSrc="rawDataCollector", minAmplitude=0.1):
    """The ECAL and HCAL digi tables (EBDigi, EEDigi, HBHEDigi): the ADC samples of every
    cell whose pedestal-subtracted amplitude on the rechit scale exceeds minAmplitude [GeV].

    The digis are unpacked here from the RAW data (rawSrc), which the RECO files do not
    carry: give the RAW file as the secondary input of the Pico step (the two-file
    solution), as the run3_mix chain's step0 output next to its step1 RECO."""
    from EventFilter.EcalRawToDigi.EcalUnpackerData_cfi import ecalEBunpacker
    from EventFilter.HcalRawToDigi.HcalRawToDigi_cfi import hcalDigis

    process.picoEcalDigis = ecalEBunpacker.clone(InputLabel=cms.InputTag(rawSrc))
    process.picoHcalDigis = hcalDigis.clone(InputLabel=cms.InputTag(rawSrc))
    process.picoEBDigiTable = cms.EDProducer(
        "PicoEBDigiTableProducer",
        src=cms.InputTag("picoEcalDigis", "ebDigis"),
        name=cms.string("EBDigi"),
        minAmplitude=cms.double(minAmplitude),
    )
    process.picoEEDigiTable = cms.EDProducer(
        "PicoEEDigiTableProducer",
        src=cms.InputTag("picoEcalDigis", "eeDigis"),
        name=cms.string("EEDigi"),
        minAmplitude=cms.double(minAmplitude),
    )
    process.picoHBHEDigiTable = cms.EDProducer(
        "PicoHcalDigiTableProducer",
        src=cms.InputTag("picoHcalDigis"),
        name=cms.string("HBHEDigi"),
        minAmplitude=cms.double(minAmplitude),
    )
    process.picoCaloDigiTask = cms.Task(
        process.picoEcalDigis, process.picoHcalDigis, process.picoEBDigiTable, process.picoEEDigiTable, process.picoHBHEDigiTable
    )
    return process.picoCaloDigiTask
