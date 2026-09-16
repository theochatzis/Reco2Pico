import json

import FWCore.ParameterSet.Config as cms


DEFAULT_PILEUP_EDGES = [float(i) for i in range(101)]


def mcBookkeeping(process, pileup_edges=None, require_pileup=True):
    """
    Add generic MC bookkeeping to Pico.

    Event-level output:
      genWeight

    Runs output:
      genEventCount
      genEventSumw
      genEventSumw2
      pileupSumw

    nanoMetadata:
      bookkeepingSchema (JSON)
    """

    if pileup_edges is None:
        pileup_edges = DEFAULT_PILEUP_EDGES

    pileup_edges = [float(x) for x in pileup_edges]

    process.picoMCBookkeepingTable = cms.EDProducer(
        "PicoMCBookkeepingProducer",

        genInfo=cms.InputTag("generator"),

        # Try MiniAOD first, then AOD/RECO.
        pileupInfo=cms.VInputTag(
            cms.InputTag("slimmedAddPileupInfo"),
            cms.InputTag("addPileupInfo"),
        ),

        pileupEdges=cms.vdouble(pileup_edges),

        requirePileup=cms.bool(require_pileup),
    )

    schema = {
        "version": 1,
        "storage": "Runs/MergeableCounterTable",
        "scalars": {
            "genEventCount": {
                "type": "int",
                "merge": "sum",
            },
            "genEventSumw": {
                "type": "float",
                "merge": "sum",
            },
            "genEventSumw2": {
                "type": "float",
                "merge": "sum",
            },
        },
        "histograms": {
            "pileup": {
                "contents": "pileupSumw",
                "edges": pileup_edges,
                "flow_bins": True,
                "weight": "genWeight",
                "variable": "Pileup_nTrueInt",
            },
        },
    }

    # NanoAODOutputModule has dedicated handling for UniqueString objects
    # produced under the module label "nanoMetadata".
    process.nanoMetadata = cms.EDProducer(
        "UniqueStringProducer",
        strings=cms.PSet(
            tag=cms.string("Reco2Pico"),
            bookkeepingSchema=cms.string(
                json.dumps(
                    schema,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
        ),
    )

    process.picoMCBookkeepingTask = cms.Task(
        process.picoMCBookkeepingTable,
        process.nanoMetadata,
    )

    return process
