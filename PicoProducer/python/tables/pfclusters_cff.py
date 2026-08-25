import FWCore.ParameterSet.Config as cms


DEFAULT_PFCLUSTERS = {
    "ECAL": "particleFlowClusterECAL",
    "HCAL": "particleFlowClusterHCAL",
    "HO": "particleFlowClusterHO",
    "HF": "particleFlowClusterHF",
    "PS": "particleFlowClusterPS",
}


def pfClusterTables(process, sources=None, minEnergy=0.0):
    """Create one FlatTable per reco::PFCluster collection.

    These collections are normally available in RECO. They are not part of
    standard AOD event content, so leave the 'pfclusters' group disabled for
    AOD unless you have explicitly produced/kept them.
    """
    sources = DEFAULT_PFCLUSTERS if sources is None else sources
    modules = []

    for suffix, src in sources.items():
        label = "picoPFCluster%sTable" % suffix
        module = cms.EDProducer(
            "PicoPFClusterTableProducer",
            src=cms.InputTag(src),
            name=cms.string("PFCluster%s" % suffix),
            minEnergy=cms.double(minEnergy),
        )
        setattr(process, label, module)
        modules.append(getattr(process, label))

    return modules
