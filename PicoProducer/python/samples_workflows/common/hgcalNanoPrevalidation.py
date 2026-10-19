# ---------------------------------------------------------------------------
# cmsDriver customisation for a standalone NANO:@HGCALVal step.
#
# The HGCAL validation NANO tables (DPGAnalysis/HGCalNanoAOD, flavour @HGCALVal)
# consume products that are NOT written by RAW2DIGI,RECO,RECOSIM:
#   * ticlSimTracksters*                        (RecoHGCal/TICL SimTracksters_cff)
#   * SimClusterToCaloParticleAssociation       (SimCalorimetry/HGCalAssociatorProducers)
#   * allTrackstersToSimTrackstersAssociationsByHits, ...
# In the relval they exist because NANO:@HGCALVal runs in the same job as
# VALIDATION:@phase2Validation (workflow suffix _HGCALNanoVal), whose
# globalPrevalidationHGCal = Sequence(hgcalAssociators, ticlSimTrackstersTask)
# produces them. A separate step4 on a GEN-SIM-RECO file therefore dies with
#   ProductNotFound ... SimClusterToCaloParticleAssociation:simClusterToCaloParticleMap
#
# This customisation attaches exactly those two Tasks to the nanoAOD path, so
# the associators run on demand before the tables, without the DQM validators.
#
# Usage (common/ntuples/hgcalval-nano.sh wires this into the ntuple step):
#   cmsDriver.py step4 -s NANO:@HGCALVal ... \
#     --customise Reco2Pico/PicoProducer/samples_workflows/common/hgcalNanoPrevalidation.customise
# ---------------------------------------------------------------------------
import FWCore.ParameterSet.Config as cms


def customise(process):
    process.load('Configuration.StandardSequences.Accelerators_cff')  # resolves the '@alpaka' ESProducers below
    process.load('RecoHGCal.TICL.TICLGeom_cff')                  # TICLGeomLayers ESProducers (loaded by RECO, not by NANO)
    process.load('Validation.Configuration.hgcalSimValid_cff')   # hgcalAssociators (Task)
    process.load('RecoHGCal.TICL.SimTracksters_cff')             # ticlSimTrackstersTask

    # Transient products that RECO / the tracking prevalidation make in the same
    # job and that are not in the GEN-SIM-RECO file. Every consumer below only
    # *warns* and produces empty maps when they are missing (so the sim tables
    # of NANO:@HGCALVal silently come out empty):
    #  * recHitMapProducer: DetId->index hit map + RefProdVector of the HGCRecHit
    #    collections ("Hit map not valid", "Missing MultiRecHitCollection", ...)
    #  * tpClusterProducer + quickTrackAssociatorByHits -> trackingParticleRecoTrackAsssociation
    #    (TP<->generalTracks; "Missing TP->RecoTrack association") and the GSF
    #    variant inside ticlSimTrackstersTask
    #  * simHitTPAssocProducer: SimTrack->TrackingParticle map read by ticlSimTracksters
    process.load('RecoLocalCalo.HGCalRecProducers.recHitMapProducer_cff')
    process.load('SimTracker.TrackerHitAssociation.tpClusterProducer_cfi')
    process.load('SimTracker.TrackAssociatorProducers.quickTrackAssociatorByHits_cfi')
    process.load('SimTracker.TrackAssociation.trackingParticleRecoTrackAsssociation_cfi')
    process.load('SimGeneral.TrackingAnalysis.simHitTPAssociation_cfi')
    process.hgcalNanoPrevalidationInputsTask = cms.Task(process.recHitMapProducer,
                                                        process.tpClusterProducer,
                                                        process.quickTrackAssociatorByHits,
                                                        process.trackingParticleRecoTrackAsssociation,
                                                        process.simHitTPAssocProducer)

    tasks = [process.hgcalNanoPrevalidationInputsTask, process.hgcalAssociators, process.ticlSimTrackstersTask]
    paths = [p for p in process.paths_().values()
             if 'nano' in p.label().lower() or p.label() == 'nanoAOD_step']
    if not paths:
        raise RuntimeError('hgcalNanoPrevalidation: no NANO path found in the process')
    for p in paths:
        p.associate(*tasks)
    print('hgcalNanoPrevalidation: reco/track inputs + hgcalAssociators + ticlSimTrackstersTask attached to '
          + ', '.join(p.label() for p in paths))
    return process
