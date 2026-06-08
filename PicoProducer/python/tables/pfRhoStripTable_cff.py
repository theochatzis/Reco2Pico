import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *

def pfRhoStripTables(process, pfcSrc="packedPFCandidates"):
    process.pfRhoStripTable = cms.EDProducer(
        "PFRhoStripTableProducer",

        src = cms.InputTag(pfcSrc),
        name = cms.string("PFRhoStrip"),

        # True: use physical HB/HE HCAL eta-phi segmentation.
        # False: use etaBins/phiBins below.
        useHCALGeometry = cms.bool(True),

        includeHB = cms.bool(True),
        includeHE = cms.bool(True),

        minPt = cms.double(0.0),

        # Used only when useHCALGeometry=False.
        etaBins = cms.vdouble(),
        phiBins = cms.vdouble(),
    )

    '''
    ## EXAMPLE: If you want custom bins instead of HCAL geometry

    pfRhoStripTableCustom = pfRhoStripTable.clone(
        useHCALGeometry = False,
        etaBins = cms.vdouble(-5.0, -3.0, -1.5, 0.0, 1.5, 3.0, 5.0),
        phiBins = cms.vdouble(
            -3.14159265359,
            -1.57079632679,
            0.0,
            1.57079632679,
            3.14159265359,
        ),
    )
    '''

    process.pfRhoStripTableTask = cms.Task(process.pfRhoStripTable)
    process.pfRhoStripTableSeq = cms.Sequence(process.pfRhoStripTableTask)

    return process