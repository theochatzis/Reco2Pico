import FWCore.ParameterSet.Config as cms

process = cms.Process("PICO")

process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring('/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root'),
    secondaryFileNames = cms.untracked.vstring(),
    skipEvents = cms.untracked.uint32(0)
)
process.CondDB = cms.PSet(
    DBParameters = cms.PSet(
        authenticationPath = cms.untracked.string(''),
        authenticationSystem = cms.untracked.int32(0),
        connectionTimeout = cms.untracked.int32(0),
        messageLevel = cms.untracked.int32(0),
        security = cms.untracked.string('')
    ),
    connect = cms.string('')
)

process.HFRecalParameterBlock = cms.PSet(
    HFdepthOneParameterA = cms.vdouble(
        0.004123, 0.00602, 0.008201, 0.010489, 0.013379,
        0.016997, 0.021464, 0.027371, 0.034195, 0.044807,
        0.058939, 0.125497
    ),
    HFdepthOneParameterB = cms.vdouble(
        -4e-06, -2e-06, 0.0, 4e-06, 1.5e-05,
        2.6e-05, 6.3e-05, 8.4e-05, 0.00016, 0.000107,
        0.000425, 0.000209
    ),
    HFdepthTwoParameterA = cms.vdouble(
        0.002861, 0.004168, 0.0064, 0.008388, 0.011601,
        0.014425, 0.018633, 0.023232, 0.028274, 0.035447,
        0.051579, 0.086593
    ),
    HFdepthTwoParameterB = cms.vdouble(
        -2e-06, -0.0, -7e-06, -6e-06, -2e-06,
        1e-06, 1.9e-05, 3.1e-05, 6.7e-05, 1.2e-05,
        0.000157, -3e-06
    )
)

process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(1000),
    output = cms.optional.untracked.allowed(cms.int32,cms.PSet)
)

process.maxLuminosityBlocks = cms.untracked.PSet(
    input = cms.untracked.int32(-1)
)

process.nanoDQMIO_perLSoutput = cms.PSet(
    MEsToSave = cms.untracked.vstring( (
        'Hcal/DigiTask/Occupancy/depth/depth1',
        'Hcal/DigiTask/Occupancy/depth/depth2',
        'Hcal/DigiTask/Occupancy/depth/depth3',
        'Hcal/DigiTask/Occupancy/depth/depth4',
        'Hcal/DigiTask/Occupancy/depth/depth5',
        'Hcal/DigiTask/Occupancy/depth/depth6',
        'Hcal/DigiTask/Occupancy/depth/depth7',
        'Hcal/DigiTask/Occupancy/depth/depthHO',
        'Hcal/DigiTask/OccupancyCut/depth/depth1',
        'Hcal/DigiTask/OccupancyCut/depth/depth2',
        'Hcal/DigiTask/OccupancyCut/depth/depth3',
        'Hcal/DigiTask/OccupancyCut/depth/depth4',
        'Hcal/DigiTask/OccupancyCut/depth/depth5',
        'Hcal/DigiTask/OccupancyCut/depth/depth6',
        'Hcal/DigiTask/OccupancyCut/depth/depth7',
        'Hcal/DigiTask/OccupancyCut/depth/depthHO',
        'EcalBarrel/EBOccupancyTask/EBOT digi occupancy',
        'EcalEndcap/EEOccupancyTask/EEOT digi occupancy EE -',
        'EcalEndcap/EEOccupancyTask/EEOT digi occupancy EE +',
        'EcalBarrel/EBOccupancyTask/EBOT DCC entries',
        'EcalEndcap/EEOccupancyTask/EEOT DCC entries',
        'Ecal/EventInfo/processedEvents',
        'PixelPhase1/Tracks/charge_PXBarrel',
        'PixelPhase1/Tracks/charge_PXForward',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-3',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm1',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm2',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm4',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp1',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp2',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp4',
        'HLT/Vertexing/hltPixelVertices/hltPixelVertices/goodvtxNbr',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_pt',
        'HLT/Tracking/pixelTracks/GeneralProperties/Chi2Prob_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/Chi2oNDFVsEta_ImpactPoint_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DeltaZToPVZoom_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DistanceOfClosestApproachToPVVsPhi_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DistanceOfClosestApproachToPVZoom_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/NumberOfTracks_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/Chi2Prob_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/Chi2oNDFVsEta_ImpactPoint_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DeltaZToPVZoom_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DistanceOfClosestApproachToPVVsPhi_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DistanceOfClosestApproachToPVZoom_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/NumberOfTracks_GenTk',
        'HLT/Tracking/tracks/LUMIanalysis/NumberEventsVsLUMI',
        'HLT/Tracking/tracks/PUmonitoring/NumberEventsVsGoodPVtx',
        'PixelPhase1/Tracks/num_clusters_ontrack_PXBarrel',
        'PixelPhase1/Tracks/num_clusters_ontrack_PXForward',
        'PixelPhase1/Tracks/clusterposition_zphi_ontrack',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_1',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_4',
        'PixelPhase1/Phase1_MechanicalView/PXForward/digi_occupancy_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_1',
        'PixelPhase1/Phase1_MechanicalView/PXForward/digi_occupancy_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_1',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_4',
        'PixelPhase1/Phase1_MechanicalView/PXForward/clusters_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_1',
        'PixelPhase1/Phase1_MechanicalView/PXForward/clusters_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/NormalizedHitResiduals_TEC__wheel__1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_2/NormalizedHitResiduals_TEC__wheel__2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_3/NormalizedHitResiduals_TEC__wheel__3',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_4/NormalizedHitResiduals_TEC__wheel__4',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_5/NormalizedHitResiduals_TEC__wheel__5',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_6/NormalizedHitResiduals_TEC__wheel__6',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_7/NormalizedHitResiduals_TEC__wheel__7',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_8/NormalizedHitResiduals_TEC__wheel__8',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_9/NormalizedHitResiduals_TEC__wheel__9',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_1/NormalizedHitResiduals_TEC__wheel__1',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_2/NormalizedHitResiduals_TEC__wheel__2',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_3/NormalizedHitResiduals_TEC__wheel__3',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_4/NormalizedHitResiduals_TEC__wheel__4',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_5/NormalizedHitResiduals_TEC__wheel__5',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_6/NormalizedHitResiduals_TEC__wheel__6',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_7/NormalizedHitResiduals_TEC__wheel__7',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_8/NormalizedHitResiduals_TEC__wheel__8',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_9/NormalizedHitResiduals_TEC__wheel__9',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__3',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_4/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__4',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_5/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__5',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_6/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__6',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_7/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__7',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_8/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__8',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_9/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__9',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__1',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__2',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__3',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_4/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__4',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_5/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__5',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_6/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__6',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_7/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__7',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_8/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__8',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_9/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__9',
        'SiStrip/MechanicalView/TIB/layer_1/NormalizedHitResiduals_TIB__Layer__1',
        'SiStrip/MechanicalView/TIB/layer_2/NormalizedHitResiduals_TIB__Layer__2',
        'SiStrip/MechanicalView/TIB/layer_3/NormalizedHitResiduals_TIB__Layer__3',
        'SiStrip/MechanicalView/TIB/layer_4/NormalizedHitResiduals_TIB__Layer__4',
        'SiStrip/MechanicalView/TIB/layer_1/Summary_ClusterStoNCorr__OnTrack__TIB__layer__1',
        'SiStrip/MechanicalView/TIB/layer_2/Summary_ClusterStoNCorr__OnTrack__TIB__layer__2',
        'SiStrip/MechanicalView/TIB/layer_3/Summary_ClusterStoNCorr__OnTrack__TIB__layer__3',
        'SiStrip/MechanicalView/TIB/layer_4/Summary_ClusterStoNCorr__OnTrack__TIB__layer__4',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/NormalizedHitResiduals_TID__wheel__1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_2/NormalizedHitResiduals_TID__wheel__2',
        'SiStrip/MechanicalView/TID/PLUS/wheel_3/NormalizedHitResiduals_TID__wheel__3',
        'SiStrip/MechanicalView/TID/MINUS/wheel_1/NormalizedHitResiduals_TID__wheel__1',
        'SiStrip/MechanicalView/TID/MINUS/wheel_2/NormalizedHitResiduals_TID__wheel__2',
        'SiStrip/MechanicalView/TID/MINUS/wheel_3/NormalizedHitResiduals_TID__wheel__3',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__2',
        'SiStrip/MechanicalView/TID/PLUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__3',
        'SiStrip/MechanicalView/TID/MINUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__1',
        'SiStrip/MechanicalView/TID/MINUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__2',
        'SiStrip/MechanicalView/TID/MINUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__3',
        'SiStrip/MechanicalView/TOB/layer_1/NormalizedHitResiduals_TOB__Layer__1',
        'SiStrip/MechanicalView/TOB/layer_2/NormalizedHitResiduals_TOB__Layer__2',
        'SiStrip/MechanicalView/TOB/layer_3/NormalizedHitResiduals_TOB__Layer__3',
        'SiStrip/MechanicalView/TOB/layer_4/NormalizedHitResiduals_TOB__Layer__4',
        'SiStrip/MechanicalView/TOB/layer_5/NormalizedHitResiduals_TOB__Layer__5',
        'SiStrip/MechanicalView/TOB/layer_6/NormalizedHitResiduals_TOB__Layer__6',
        'SiStrip/MechanicalView/TOB/layer_1/Summary_ClusterStoNCorr__OnTrack__TOB__layer__1',
        'SiStrip/MechanicalView/TOB/layer_2/Summary_ClusterStoNCorr__OnTrack__TOB__layer__2',
        'SiStrip/MechanicalView/TOB/layer_3/Summary_ClusterStoNCorr__OnTrack__TOB__layer__3',
        'SiStrip/MechanicalView/TOB/layer_4/Summary_ClusterStoNCorr__OnTrack__TOB__layer__4',
        'SiStrip/MechanicalView/TOB/layer_5/Summary_ClusterStoNCorr__OnTrack__TOB__layer__5',
        'SiStrip/MechanicalView/TOB/layer_6/Summary_ClusterStoNCorr__OnTrack__TOB__layer__6',
        'SiStrip/MechanicalView/MainDiagonal Position',
        'SiStrip/MechanicalView/NumberOfClustersInPixel',
        'SiStrip/MechanicalView/NumberOfClustersInStrip',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/TkHMap_NumberOfDigi_TIDP_D1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/TkHMap_NumberOfCluster_TIDP_D1',
        'SiStrip/MechanicalView/TIB/layer_1/TkHMap_NumberOfDigi_TIB_L1',
        'SiStrip/MechanicalView/TIB/layer_1/TkHMap_NumberOfCluster_TIB_L1',
        'SiStrip/MechanicalView/TOB/layer_1/TkHMap_NumberOfDigi_TOB_L1',
        'SiStrip/MechanicalView/TOB/layer_1/TkHMap_NumberOfCluster_TOB_L1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/TkHMap_NumberOfDigi_TECP_W1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/TkHMap_NumberOfCluster_TECP_W1',
        'Tracking/TrackParameters/generalTracks/LSanalysis/Chi2oNDF_lumiFlag_GenTk',
        'Tracking/TrackParameters/generalTracks/LSanalysis/NumberOfRecHitsPerTrack_lumiFlag_GenTk',
        'Tracking/TrackParameters/generalTracks/LSanalysis/NumberOfTracks_lumiFlag_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIPDxyToPV_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIPDzToPV_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIP3DToPV_GenTk',
        'Tracking/TrackParameters/generalTracks/HitProperties/NumberOfMissingOuterRecHitsPerTrack_GenTk',
        'Tracking/TrackParameters/generalTracks/HitProperties/NumberMORecHitsPerTrackVsPt_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackEtaPhi_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/NumberOfTracks_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackPt_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/Chi2oNDF_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackPhi_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackEta_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_Strip_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_Pixel_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBS_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSdz_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSVsPhi_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSVsEta_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackQoverP_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/Quality_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_Hardvtx_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_PUvtx_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtHighpurity_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtTight_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtLoose_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaHighpurity_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaTight_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaLoose_ImpactPoint_GenTk',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/NumberOfGoodPVtx_offline',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/GoodPVtxNumberOfTracks_offline',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_Hardvtx_PUvtx_GenTk',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/FractionOfGoodPVtx_offline',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_Ratio_byFoldingmap_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_Ratio_byFoldingmap_op_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_RelativeDifference_byFoldingmap_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_RelativeDifference_byFoldingmap_op_ImpactPoint_GenTk',
        'OfflinePV/offlinePrimaryVertices/tagVtxProb',
        'OfflinePV/offlinePrimaryVertices/tagType',
        'OfflinePV/Resolution/PV/pull_x',
        'OfflinePV/Resolution/PV/pull_y',
        'OfflinePV/Resolution/PV/pull_z',
        'OfflinePV/offlinePrimaryVertices/tagDiffX',
        'OfflinePV/offlinePrimaryVertices/tagDiffY',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_highPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_highPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_mediumPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_mediumPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_lowPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_lowPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_highPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_highPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_mediumPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_mediumPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_lowPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_lowPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Constituents',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Eta',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Eta_uncor',
        'JetMET/Jet/Cleanedak4PFJetsCHS/JetEnergyCorr',
        'JetMET/Jet/Cleanedak4PFJetsCHS/NJets',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Pt',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/PtJetMET/Jet/Cleanedak4PFJetsPuppi/Phi',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Phi_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Phi_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/JetEnergyCorr',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/NJets',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Eta',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Eta_uncor',
        'JetMET/MET/pfMETT1/Cleaned/METSig',
        'JetMET/vertices',
        'JetMET/HIJetValidation/akCs4PFJets/SumPFPt',
        'JetMET/HIJetValidation/akCs4PFJets/NJets',
        'JetMET/HIJetValidation/akCs4PFJets/NPFpart',
        'JetMET/HIJetValidation/akPu4CaloJets/SumCaloPt',
        'JetMET/HIJetValidation/akPu4CaloJets/NCalopart',
        'JetMET/HIJetValidation/akPu4CaloJets/NJets',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_pt',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_eta',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_phi',
        'Muons/MuonRecoAnalyzer/Res_TkGlb_qOverlap',
        'Muons/diMuonHistograms/GlbGlbMuon_LM',
        'Muons/diMuonHistograms/GlbGlbMuon_HM',
        'Muons/Isolation/global/relPFIso_R03',
        'Muons/globalMuons/GeneralProperties/NumberOfMeanRecHitsPerTrack_glb',
        'Muons/standAloneMuonsUpdatedAtVtx/HitProperties/NumberOfValidRecHitsPerTrack_sta',
        'Muons/MuonRecoOneHLT/GlbMuon_Glb_pt',
        'Muons/MuonRecoOneHLT/GlbMuon_Glb_eta',
        'Egamma/Electrons/Ele5_TagAndProbe/ele0_vertexPt_barrel',
        'Egamma/Electrons/Ele5_TagAndProbe/ele1_vertexPt_endcaps',
        'Egamma/Electrons/Ele5_TagAndProbe/ele2_vertexEta',
        'Egamma/Electrons/Ele5_TagAndProbe/ele5_vertexZ',
        'Egamma/Electrons/Ele5_TagAndProbe/ele10_Eop_barrel',
        'Egamma/Electrons/Ele5_TagAndProbe/ele10_Eop_endcaps',
        'Egamma/Electrons/Ele5_TagAndProbe/ele101_etaEff',
        'Egamma/Electrons/Ele5_TagAndProbe/ele102_phiEff',
        'Egamma/Electrons/Ele5_TagAndProbe/ele201_mee_os'
     ) )
)

process.options = cms.untracked.PSet(
    IgnoreCompletely = cms.untracked.vstring(),
    Rethrow = cms.untracked.vstring(),
    TryToContinue = cms.untracked.vstring(),
    accelerators = cms.untracked.vstring('*'),
    allowUnscheduled = cms.obsolete.untracked.bool,
    canDeleteEarly = cms.untracked.vstring(),
    deleteNonConsumedUnscheduledModules = cms.untracked.bool(True),
    dumpOptions = cms.untracked.bool(False),
    emptyRunLumiMode = cms.obsolete.untracked.string,
    eventSetup = cms.untracked.PSet(
        forceNumberOfConcurrentIOVs = cms.untracked.PSet(
            allowAnyLabel_=cms.required.untracked.uint32
        ),
        numberOfConcurrentIOVs = cms.untracked.uint32(0)
    ),
    fileMode = cms.untracked.string('FULLMERGE'),
    forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
    holdsReferencesToDeleteEarly = cms.untracked.VPSet(),
    makeTriggerResults = cms.obsolete.untracked.bool,
    modulesToCallForTryToContinue = cms.untracked.vstring(),
    modulesToIgnoreForDeleteEarly = cms.untracked.vstring(),
    numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(0),
    numberOfConcurrentRuns = cms.untracked.uint32(1),
    numberOfStreams = cms.untracked.uint32(0),
    numberOfThreads = cms.untracked.uint32(1),
    printDependencies = cms.untracked.bool(False),
    sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
    throwIfIllegalParameter = cms.untracked.bool(True),
    wantSummary = cms.untracked.bool(False)
)

process.pfPuppiRhoStripTable = cms.EDProducer("PFRhoStripTableProducer",
    etaBins = cms.vdouble(),
    includeHB = cms.bool(True),
    includeHE = cms.bool(True),
    minPt = cms.double(0.0),
    name = cms.string('PFPuppiRhoStrip'),
    phiBins = cms.vdouble(),
    src = cms.InputTag("packedPFCandidates"),
    useHCALGeometry = cms.bool(True),
    usePuppiWeights = cms.bool(True)
)


process.pfRhoStripTable = cms.EDProducer("PFRhoStripTableProducer",
    etaBins = cms.vdouble(),
    includeHB = cms.bool(True),
    includeHE = cms.bool(True),
    minPt = cms.double(0.0),
    name = cms.string('PFRhoStrip'),
    phiBins = cms.vdouble(),
    src = cms.InputTag("packedPFCandidates"),
    useHCALGeometry = cms.bool(True)
)


process.picoElectronTable = cms.EDProducer("SimplePATElectronFlatTableProducer",
    cut = cms.string(''),
    doc = cms.string('Electrons for PicoAOD'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('Electron'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedElectrons"),
    variables = cms.PSet(
        charge = cms.PSet(
            doc = cms.string('electric charge'),
            expr = cms.string('charge'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        cutBasedID_loose = cms.PSet(
            doc = cms.string('RunIIIWinter22 V1 loose cut-based electron ID'),
            expr = cms.string("userInt(\'cutBasedElectronID-RunIIIWinter22-V1-loose\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        cutBasedID_medium = cms.PSet(
            doc = cms.string('RunIIIWinter22 V1 medium cut-based electron ID'),
            expr = cms.string("userInt(\'cutBasedElectronID-RunIIIWinter22-V1-medium\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        cutBasedID_tight = cms.PSet(
            doc = cms.string('RunIIIWinter22 V1 tight cut-based electron ID'),
            expr = cms.string("userInt(\'cutBasedElectronID-RunIIIWinter22-V1-tight\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        cutBasedID_veto = cms.PSet(
            doc = cms.string('RunIIIWinter22 V1 veto cut-based electron ID'),
            expr = cms.string("userInt(\'cutBasedElectronID-RunIIIWinter22-V1-veto\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        eta = cms.PSet(
            doc = cms.string('eta'),
            expr = cms.string('eta'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        mass = cms.PSet(
            doc = cms.string('mass'),
            expr = cms.string('mass'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(10),
            type = cms.string('float')
        ),
        pdgId = cms.PSet(
            doc = cms.string('PDG code assigned by the event reconstruction (not by MC truth)'),
            expr = cms.string('pdgId'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('float')
        )
    )
)


process.picoGenJetTable = cms.EDProducer("SimpleGenJetFlatTableProducer",
    cut = cms.string('pt > 10'),
    doc = cms.string('AK4 generator-level jets'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('GenJet'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedGenJets"),
    variables = cms.PSet(
        eta = cms.PSet(
            doc = cms.string('eta'),
            expr = cms.string('eta'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        mass = cms.PSet(
            doc = cms.string('mass'),
            expr = cms.string('mass'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(10),
            type = cms.string('float')
        ),
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('float')
        )
    )
)


process.picoJetMCTable = cms.EDProducer("SimplePATJetFlatTableProducer",
    cut = cms.string(''),
    doc = cms.string(''),
    extension = cms.bool(True),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('Jet'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedJetsPuppi"),
    variables = cms.PSet(
        genJetIdx = cms.PSet(
            doc = cms.string('index of matched gen jet'),
            expr = cms.string('?genJetFwdRef().backRef().isNonnull() && genJetFwdRef().backRef().pt() > 10.?genJetFwdRef().backRef().key():-1'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int16')
        )
    )
)


process.picoJetTable = cms.EDProducer("SimplePATJetFlatTableProducer",
    cut = cms.string(''),
    doc = cms.string('AK4 PUPPI jets for PicoAOD'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('Jet'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedJetsPuppi"),
    variables = cms.PSet(
        area = cms.PSet(
            doc = cms.string('jet area'),
            expr = cms.string('jetArea()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(10),
            type = cms.string('float')
        ),
        chEmEF = cms.PSet(
            doc = cms.string('charged Electromagnetic Energy Fraction'),
            expr = cms.string('chargedEmEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        chHEF = cms.PSet(
            doc = cms.string('charged Hadron Energy Fraction'),
            expr = cms.string('chargedHadronEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        chMultiplicity = cms.PSet(
            doc = cms.string('(Puppi-weighted) Number of charged particles in the jet'),
            expr = cms.string('chargedMultiplicity()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        eta = cms.PSet(
            doc = cms.string('eta'),
            expr = cms.string('eta'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        hfEmEF = cms.PSet(
            doc = cms.string('electromagnetic Energy Fraction in HF'),
            expr = cms.string('HFEMEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        hfHEF = cms.PSet(
            doc = cms.string('hadronic Energy Fraction in HF'),
            expr = cms.string('HFHadronEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        mass = cms.PSet(
            doc = cms.string('mass'),
            expr = cms.string('mass'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(10),
            type = cms.string('float')
        ),
        muEF = cms.PSet(
            doc = cms.string('muon Energy Fraction'),
            expr = cms.string('muonEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        nConstituents = cms.PSet(
            doc = cms.string('Number of particles in the jet'),
            expr = cms.string('numberOfDaughters()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        neEmEF = cms.PSet(
            doc = cms.string('neutral Electromagnetic Energy Fraction'),
            expr = cms.string('neutralEmEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        neHEF = cms.PSet(
            doc = cms.string('neutral Hadron Energy Fraction'),
            expr = cms.string('neutralHadronEnergyFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        neMultiplicity = cms.PSet(
            doc = cms.string('(Puppi-weighted) Number of neutral particles in the jet'),
            expr = cms.string('neutralMultiplicity()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('float')
        ),
        rawFactor = cms.PSet(
            doc = cms.string('1 - Factor to get back to raw pT'),
            expr = cms.string("1.-jecFactor(\'Uncorrected\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        )
    )
)


process.picoMETTable = cms.EDProducer("SimplePATMETFlatTableProducer",
    doc = cms.string('PUPPI MET for PicoAOD'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('PuppiMET'),
    singleton = cms.bool(True),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedMETsPuppi"),
    variables = cms.PSet(
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('float')
        )
    )
)


process.picoMuonTable = cms.EDProducer("SimplePATMuonFlatTableProducer",
    cut = cms.string(''),
    doc = cms.string('Muons for PicoAOD'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('Muon'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedMuons"),
    variables = cms.PSet(
        charge = cms.PSet(
            doc = cms.string('electric charge'),
            expr = cms.string('charge'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        eta = cms.PSet(
            doc = cms.string('eta'),
            expr = cms.string('eta'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        looseId = cms.PSet(
            doc = cms.string('muon is loose muon'),
            expr = cms.string("passed(\'CutBasedIdLoose\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('bool')
        ),
        mass = cms.PSet(
            doc = cms.string('mass'),
            expr = cms.string('mass'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(10),
            type = cms.string('float')
        ),
        mediumId = cms.PSet(
            doc = cms.string('cut-based ID, medium WP'),
            expr = cms.string("passed(\'CutBasedIdMedium\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('bool')
        ),
        pdgId = cms.PSet(
            doc = cms.string('PDG code assigned by the event reconstruction (not by MC truth)'),
            expr = cms.string('pdgId'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        pfIsoId = cms.PSet(
            doc = cms.string('PFIso ID from miniAOD selector (1=PFIsoVeryLoose, 2=PFIsoLoose, 3=PFIsoMedium, 4=PFIsoTight, 5=PFIsoVeryTight, 6=PFIsoVeryVeryTight)'),
            expr = cms.string("passed(\'PFIsoVeryLoose\')+passed(\'PFIsoLoose\')+passed(\'PFIsoMedium\')+passed(\'PFIsoTight\')+passed(\'PFIsoVeryTight\')+passed(\'PFIsoVeryVeryTight\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        pfRelIso04_all = cms.PSet(
            doc = cms.string('PF relative isolation, dR=0.4, delta-beta corrected'),
            expr = cms.string('(pfIsolationR04().sumChargedHadronPt + max(pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt - 0.5*pfIsolationR04().sumPUPt, 0.0)) / pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(12),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('float')
        ),
        tightId = cms.PSet(
            doc = cms.string('cut-based ID, tight WP'),
            expr = cms.string("passed(\'CutBasedIdTight\')"),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('bool')
        )
    )
)


process.picoPFCandTable = cms.EDProducer("SimplePATCandidateFlatTableProducer",
    cut = cms.string('pt > 0.0 && abs(eta) < 5.0'),
    doc = cms.string('selected packed PF candidates for PicoAOD'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    lazyEval = cms.untracked.bool(False),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('PFCand'),
    singleton = cms.bool(False),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("packedPFCandidates"),
    variables = cms.PSet(
        caloEnergy = cms.PSet(
            doc = cms.string('Stored ECAL+HCAL energy'),
            expr = cms.string('energy*caloFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        caloFraction = cms.PSet(
            doc = cms.string('(ECAL+HCAL energy)/candidate energy'),
            expr = cms.string('caloFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        charge = cms.PSet(
            doc = cms.string('PF candidate electric charge'),
            expr = cms.string('charge'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        dxy = cms.PSet(
            doc = cms.string('dxy relative to associated PV'),
            expr = cms.string('dxy()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        dz = cms.PSet(
            doc = cms.string('dz relative to associated PV'),
            expr = cms.string('dz()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        ecalEnergy = cms.PSet(
            doc = cms.string('Stored ECAL energy'),
            expr = cms.string('energy*caloFraction()*(1-hcalFraction())'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        energy = cms.PSet(
            doc = cms.string('PF candidate energy'),
            expr = cms.string('energy'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        eta = cms.PSet(
            doc = cms.string('PF candidate eta'),
            expr = cms.string('eta'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        fromPV = cms.PSet(
            doc = cms.string('PackedCandidate PV association'),
            expr = cms.string('fromPV()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        hcalEnergy = cms.PSet(
            doc = cms.string('Stored HCAL energy'),
            expr = cms.string('energy*caloFraction()*hcalFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        hcalFraction = cms.PSet(
            doc = cms.string('HCAL fraction of calorimeter energy'),
            expr = cms.string('hcalFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        isIsolatedChargedHadron = cms.PSet(
            doc = cms.string('MiniAOD isolated charged-hadron flag'),
            expr = cms.string('isIsolatedChargedHadron()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('bool')
        ),
        mass = cms.PSet(
            doc = cms.string('PF candidate mass'),
            expr = cms.string('mass'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        pdgId = cms.PSet(
            doc = cms.string('PF candidate PDG/PF type'),
            expr = cms.string('pdgId'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('int')
        ),
        phi = cms.PSet(
            doc = cms.string('PF candidate phi'),
            expr = cms.string('phi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('Unweighted PF candidate pT'),
            expr = cms.string('pt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        ptTrk = cms.PSet(
            doc = cms.string('Track transverse momentum stored in PackedCandidate'),
            expr = cms.string('ptTrk()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        puppiWeight = cms.PSet(
            doc = cms.string('Existing PUPPI weight'),
            expr = cms.string('puppiWeight()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        puppiWeightNoLep = cms.PSet(
            doc = cms.string('Existing no-lepton PUPPI weight'),
            expr = cms.string('puppiWeightNoLep()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        rawCaloEnergy = cms.PSet(
            doc = cms.string('Raw ECAL+HCAL energy for isolated charged hadrons'),
            expr = cms.string('energy*rawCaloFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        rawCaloFraction = cms.PSet(
            doc = cms.string('Raw (ECAL+HCAL)/candidate energy for isolated charged hadrons'),
            expr = cms.string('rawCaloFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        rawEcalEnergy = cms.PSet(
            doc = cms.string('Raw ECAL energy for isolated charged hadrons'),
            expr = cms.string('energy*rawCaloFraction()*(1-rawHcalFraction())'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        rawHcalEnergy = cms.PSet(
            doc = cms.string('Raw HCAL energy for isolated charged hadrons'),
            expr = cms.string('energy*rawCaloFraction()*rawHcalFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        rawHcalFraction = cms.PSet(
            doc = cms.string('Raw HCAL fraction for isolated charged hadrons'),
            expr = cms.string('rawHcalFraction()'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        )
    )
)


process.picoRawMETTable = cms.EDProducer("SimplePATMETFlatTableProducer",
    doc = cms.string('raw Puppi MET'),
    extension = cms.bool(False),
    externalVariables = cms.PSet(

    ),
    maxLen = cms.optional.uint32,
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('RawPuppiMET'),
    singleton = cms.bool(True),
    skipNonExistingSrc = cms.bool(False),
    src = cms.InputTag("slimmedMETsPuppi"),
    variables = cms.PSet(
        phi = cms.PSet(
            doc = cms.string('phi'),
            expr = cms.string('uncorPhi'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        pt = cms.PSet(
            doc = cms.string('pt'),
            expr = cms.string('uncorPt'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        )
    )
)


process.picoVertexTable = cms.EDProducer("PicoVertexTableProducer",
    goodPvCut = cms.string('!isFake && ndof > 4 && abs(z) <= 24 && position.Rho <= 2'),
    pfcSrc = cms.InputTag("packedPFCandidates"),
    pvName = cms.string('PV'),
    pvSrc = cms.InputTag("offlineSlimmedPrimaryVertices"),
    variables = cms.PSet(
        chi2 = cms.PSet(
            doc = cms.string('main primary vertex reduced chi2'),
            expr = cms.string('chi2'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        ndof = cms.PSet(
            doc = cms.string('main primary vertex number of degree of freedom'),
            expr = cms.string('ndof'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        npvs = cms.PSet(
            doc = cms.string('total number of reconstructed primary vertices'),
            expr = cms.string('npvs'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        npvsGood = cms.PSet(
            doc = cms.string('number of good reconstructed primary vertices. selection: !isFake && ndof > 4 && abs(z) <= 24 && position.Rho <= 2'),
            expr = cms.string('npvsGood'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(-1),
            type = cms.string('uint8')
        ),
        score = cms.PSet(
            doc = cms.string('main primary vertex score, i.e. sum pt2 of clustered objects'),
            expr = cms.string('score'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        sumpt2 = cms.PSet(
            doc = cms.string('sum pt2 of pf charged candidates for the main primary vertex'),
            expr = cms.string('sumpt2'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        sumpx = cms.PSet(
            doc = cms.string('sum px of pf charged candidates for the main primary vertex'),
            expr = cms.string('sumpx'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        sumpy = cms.PSet(
            doc = cms.string('sum py of pf charged candidates for the main primary vertex'),
            expr = cms.string('sumpy'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(4),
            type = cms.string('float')
        ),
        x = cms.PSet(
            doc = cms.string('main primary vertex position x coordinate'),
            expr = cms.string('x'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        y = cms.PSet(
            doc = cms.string('main primary vertex position y coordinate'),
            expr = cms.string('y'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        ),
        z = cms.PSet(
            doc = cms.string('main primary vertex position z coordinate'),
            expr = cms.string('z'),
            lazyEval = cms.untracked.bool(False),
            precision = cms.int32(6),
            type = cms.string('float')
        )
    )
)


process.puTable = cms.EDProducer("NPUTablesProducer",
    pvsrc = cms.InputTag("offlineSlimmedPrimaryVertices"),
    savePtHatMax = cms.bool(False),
    src = cms.InputTag("slimmedAddPileupInfo"),
    zbins = cms.vdouble(
        0.0, 1.7, 2.6, 3.0, 3.5,
        4.2, 5.2, 6.0, 7.5, 9.0,
        12.0
    )
)


process.randomEngineStateProducer = cms.EDProducer("RandomEngineStateProducer")


process.rhoTable = cms.EDProducer("GlobalVariablesTableProducer",
    extension = cms.bool(False),
    mightGet = cms.optional.untracked.vstring,
    name = cms.string('Rho'),
    variables = cms.PSet(
        fixedGridRhoAll = cms.PSet(
            doc = cms.string('rho from all PF Candidates, no foreground removal'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoAll"),
            type = cms.string('double')
        ),
        fixedGridRhoFastjetAll = cms.PSet(
            doc = cms.string('rho from all PF Candidates, used e.g. for JECs'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoFastjetAll"),
            type = cms.string('double')
        ),
        fixedGridRhoFastjetCentral = cms.PSet(
            doc = cms.string('rho from all PF Candidates in the central region'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoFastjetCentral"),
            type = cms.string('double')
        ),
        fixedGridRhoFastjetCentralCalo = cms.PSet(
            doc = cms.string('rho from calo towers with |eta| < 2.5'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoFastjetCentralCalo"),
            type = cms.string('double')
        ),
        fixedGridRhoFastjetCentralChargedPileUp = cms.PSet(
            doc = cms.string('rho from charged pileup PF Candidates in the central region'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoFastjetCentralChargedPileUp"),
            type = cms.string('double')
        ),
        fixedGridRhoFastjetCentralNeutral = cms.PSet(
            doc = cms.string('rho from neutral PF Candidates with |eta| < 2.5'),
            precision = cms.int32(-1),
            src = cms.InputTag("fixedGridRhoFastjetCentralNeutral"),
            type = cms.string('double')
        )
    )
)


process.out = cms.OutputModule("NanoAODOutputModule",
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('p')
    ),
    compressionAlgorithm = cms.untracked.string('LZMA'),
    compressionLevel = cms.untracked.int32(4),
    fileName = cms.untracked.string('test_pico.root'),
    outputCommands = cms.untracked.vstring(
        'drop *',
        'keep edmTriggerResults_*_*_*',
        'keep nanoaodFlatTable_*Table_*_*',
        'keep nanoaodUniqueString_nanoMetadata_*_*'
    )
)


process.DQMStore = cms.Service("DQMStore",
    MEsToSave = cms.untracked.vstring( (
        'Hcal/DigiTask/Occupancy/depth/depth1',
        'Hcal/DigiTask/Occupancy/depth/depth2',
        'Hcal/DigiTask/Occupancy/depth/depth3',
        'Hcal/DigiTask/Occupancy/depth/depth4',
        'Hcal/DigiTask/Occupancy/depth/depth5',
        'Hcal/DigiTask/Occupancy/depth/depth6',
        'Hcal/DigiTask/Occupancy/depth/depth7',
        'Hcal/DigiTask/Occupancy/depth/depthHO',
        'Hcal/DigiTask/OccupancyCut/depth/depth1',
        'Hcal/DigiTask/OccupancyCut/depth/depth2',
        'Hcal/DigiTask/OccupancyCut/depth/depth3',
        'Hcal/DigiTask/OccupancyCut/depth/depth4',
        'Hcal/DigiTask/OccupancyCut/depth/depth5',
        'Hcal/DigiTask/OccupancyCut/depth/depth6',
        'Hcal/DigiTask/OccupancyCut/depth/depth7',
        'Hcal/DigiTask/OccupancyCut/depth/depthHO',
        'EcalBarrel/EBOccupancyTask/EBOT digi occupancy',
        'EcalEndcap/EEOccupancyTask/EEOT digi occupancy EE -',
        'EcalEndcap/EEOccupancyTask/EEOT digi occupancy EE +',
        'EcalBarrel/EBOccupancyTask/EBOT DCC entries',
        'EcalEndcap/EEOccupancyTask/EEOT DCC entries',
        'Ecal/EventInfo/processedEvents',
        'PixelPhase1/Tracks/charge_PXBarrel',
        'PixelPhase1/Tracks/charge_PXForward',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/charge_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/charge_PXDisk_-3',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/size_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/size_PXDisk_-3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm1',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm2',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalm4',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp1',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp2',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp3',
        'CSC/CSCOfflineMonitor/recHits/hRHGlobalp4',
        'HLT/Vertexing/hltPixelVertices/hltPixelVertices/goodvtxNbr',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/mon_unMatched_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_eta',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_hits',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_matched_pt',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_phi',
        'HLT/Tracking/ValidationWRTOffline/hltMergedWrtHighPurityPV/ref_pt',
        'HLT/Tracking/pixelTracks/GeneralProperties/Chi2Prob_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/Chi2oNDFVsEta_ImpactPoint_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DeltaZToPVZoom_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DistanceOfClosestApproachToPVVsPhi_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/DistanceOfClosestApproachToPVZoom_GenTk',
        'HLT/Tracking/pixelTracks/GeneralProperties/NumberOfTracks_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/Chi2Prob_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/Chi2oNDFVsEta_ImpactPoint_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DeltaZToPVZoom_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DistanceOfClosestApproachToPVVsPhi_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/DistanceOfClosestApproachToPVZoom_GenTk',
        'HLT/Tracking/tracks/GeneralProperties/NumberOfTracks_GenTk',
        'HLT/Tracking/tracks/LUMIanalysis/NumberEventsVsLUMI',
        'HLT/Tracking/tracks/PUmonitoring/NumberEventsVsGoodPVtx',
        'PixelPhase1/Tracks/num_clusters_ontrack_PXBarrel',
        'PixelPhase1/Tracks/num_clusters_ontrack_PXForward',
        'PixelPhase1/Tracks/clusterposition_zphi_ontrack',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_1',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_2',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_3',
        'PixelPhase1/Tracks/PXBarrel/clusterposition_zphi_ontrack_PXLayer_4',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+1',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+2',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_+3',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-1',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-2',
        'PixelPhase1/Tracks/PXForward/clusterposition_xy_ontrack_PXDisk_-3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_1',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/digi_occupancy_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_4',
        'PixelPhase1/Phase1_MechanicalView/PXForward/digi_occupancy_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_1',
        'PixelPhase1/Phase1_MechanicalView/PXForward/digi_occupancy_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_1',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_2',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_3',
        'PixelPhase1/Phase1_MechanicalView/PXBarrel/clusters_per_SignedModuleCoord_per_SignedLadderCoord_PXLayer_4',
        'PixelPhase1/Phase1_MechanicalView/PXForward/clusters_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_1',
        'PixelPhase1/Phase1_MechanicalView/PXForward/clusters_per_SignedDiskCoord_per_SignedBladePanelCoord_PXRing_2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/NormalizedHitResiduals_TEC__wheel__1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_2/NormalizedHitResiduals_TEC__wheel__2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_3/NormalizedHitResiduals_TEC__wheel__3',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_4/NormalizedHitResiduals_TEC__wheel__4',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_5/NormalizedHitResiduals_TEC__wheel__5',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_6/NormalizedHitResiduals_TEC__wheel__6',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_7/NormalizedHitResiduals_TEC__wheel__7',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_8/NormalizedHitResiduals_TEC__wheel__8',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_9/NormalizedHitResiduals_TEC__wheel__9',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_1/NormalizedHitResiduals_TEC__wheel__1',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_2/NormalizedHitResiduals_TEC__wheel__2',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_3/NormalizedHitResiduals_TEC__wheel__3',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_4/NormalizedHitResiduals_TEC__wheel__4',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_5/NormalizedHitResiduals_TEC__wheel__5',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_6/NormalizedHitResiduals_TEC__wheel__6',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_7/NormalizedHitResiduals_TEC__wheel__7',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_8/NormalizedHitResiduals_TEC__wheel__8',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_9/NormalizedHitResiduals_TEC__wheel__9',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__2',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__3',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_4/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__4',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_5/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__5',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_6/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__6',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_7/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__7',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_8/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__8',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_9/Summary_ClusterStoNCorr__OnTrack__TEC__PLUS__wheel__9',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__1',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__2',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__3',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_4/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__4',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_5/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__5',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_6/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__6',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_7/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__7',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_8/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__8',
        'SiStrip/MechanicalView/TEC/MINUS/wheel_9/Summary_ClusterStoNCorr__OnTrack__TEC__MINUS__wheel__9',
        'SiStrip/MechanicalView/TIB/layer_1/NormalizedHitResiduals_TIB__Layer__1',
        'SiStrip/MechanicalView/TIB/layer_2/NormalizedHitResiduals_TIB__Layer__2',
        'SiStrip/MechanicalView/TIB/layer_3/NormalizedHitResiduals_TIB__Layer__3',
        'SiStrip/MechanicalView/TIB/layer_4/NormalizedHitResiduals_TIB__Layer__4',
        'SiStrip/MechanicalView/TIB/layer_1/Summary_ClusterStoNCorr__OnTrack__TIB__layer__1',
        'SiStrip/MechanicalView/TIB/layer_2/Summary_ClusterStoNCorr__OnTrack__TIB__layer__2',
        'SiStrip/MechanicalView/TIB/layer_3/Summary_ClusterStoNCorr__OnTrack__TIB__layer__3',
        'SiStrip/MechanicalView/TIB/layer_4/Summary_ClusterStoNCorr__OnTrack__TIB__layer__4',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/NormalizedHitResiduals_TID__wheel__1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_2/NormalizedHitResiduals_TID__wheel__2',
        'SiStrip/MechanicalView/TID/PLUS/wheel_3/NormalizedHitResiduals_TID__wheel__3',
        'SiStrip/MechanicalView/TID/MINUS/wheel_1/NormalizedHitResiduals_TID__wheel__1',
        'SiStrip/MechanicalView/TID/MINUS/wheel_2/NormalizedHitResiduals_TID__wheel__2',
        'SiStrip/MechanicalView/TID/MINUS/wheel_3/NormalizedHitResiduals_TID__wheel__3',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__2',
        'SiStrip/MechanicalView/TID/PLUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TID__PLUS__wheel__3',
        'SiStrip/MechanicalView/TID/MINUS/wheel_1/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__1',
        'SiStrip/MechanicalView/TID/MINUS/wheel_2/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__2',
        'SiStrip/MechanicalView/TID/MINUS/wheel_3/Summary_ClusterStoNCorr__OnTrack__TID__MINUS__wheel__3',
        'SiStrip/MechanicalView/TOB/layer_1/NormalizedHitResiduals_TOB__Layer__1',
        'SiStrip/MechanicalView/TOB/layer_2/NormalizedHitResiduals_TOB__Layer__2',
        'SiStrip/MechanicalView/TOB/layer_3/NormalizedHitResiduals_TOB__Layer__3',
        'SiStrip/MechanicalView/TOB/layer_4/NormalizedHitResiduals_TOB__Layer__4',
        'SiStrip/MechanicalView/TOB/layer_5/NormalizedHitResiduals_TOB__Layer__5',
        'SiStrip/MechanicalView/TOB/layer_6/NormalizedHitResiduals_TOB__Layer__6',
        'SiStrip/MechanicalView/TOB/layer_1/Summary_ClusterStoNCorr__OnTrack__TOB__layer__1',
        'SiStrip/MechanicalView/TOB/layer_2/Summary_ClusterStoNCorr__OnTrack__TOB__layer__2',
        'SiStrip/MechanicalView/TOB/layer_3/Summary_ClusterStoNCorr__OnTrack__TOB__layer__3',
        'SiStrip/MechanicalView/TOB/layer_4/Summary_ClusterStoNCorr__OnTrack__TOB__layer__4',
        'SiStrip/MechanicalView/TOB/layer_5/Summary_ClusterStoNCorr__OnTrack__TOB__layer__5',
        'SiStrip/MechanicalView/TOB/layer_6/Summary_ClusterStoNCorr__OnTrack__TOB__layer__6',
        'SiStrip/MechanicalView/MainDiagonal Position',
        'SiStrip/MechanicalView/NumberOfClustersInPixel',
        'SiStrip/MechanicalView/NumberOfClustersInStrip',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/TkHMap_NumberOfDigi_TIDP_D1',
        'SiStrip/MechanicalView/TID/PLUS/wheel_1/TkHMap_NumberOfCluster_TIDP_D1',
        'SiStrip/MechanicalView/TIB/layer_1/TkHMap_NumberOfDigi_TIB_L1',
        'SiStrip/MechanicalView/TIB/layer_1/TkHMap_NumberOfCluster_TIB_L1',
        'SiStrip/MechanicalView/TOB/layer_1/TkHMap_NumberOfDigi_TOB_L1',
        'SiStrip/MechanicalView/TOB/layer_1/TkHMap_NumberOfCluster_TOB_L1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/TkHMap_NumberOfDigi_TECP_W1',
        'SiStrip/MechanicalView/TEC/PLUS/wheel_1/TkHMap_NumberOfCluster_TECP_W1',
        'Tracking/TrackParameters/generalTracks/LSanalysis/Chi2oNDF_lumiFlag_GenTk',
        'Tracking/TrackParameters/generalTracks/LSanalysis/NumberOfRecHitsPerTrack_lumiFlag_GenTk',
        'Tracking/TrackParameters/generalTracks/LSanalysis/NumberOfTracks_lumiFlag_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIPDxyToPV_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIPDzToPV_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/SIP3DToPV_GenTk',
        'Tracking/TrackParameters/generalTracks/HitProperties/NumberOfMissingOuterRecHitsPerTrack_GenTk',
        'Tracking/TrackParameters/generalTracks/HitProperties/NumberMORecHitsPerTrackVsPt_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackEtaPhi_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/NumberOfTracks_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackPt_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/Chi2oNDF_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackPhi_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackEta_ImpactPoint_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_Strip_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/HitProperties/NumberOfRecHitsPerTrack_Pixel_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBS_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSdz_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSVsPhi_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/DistanceOfClosestApproachToBSVsEta_GenTk',
        'Tracking/TrackParameters/highPurityTracks/pt_1/GeneralProperties/TrackQoverP_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/Quality_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_Hardvtx_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_PUvtx_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtHighpurity_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtTight_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackPtLoose_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaHighpurity_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaTight_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TrackEtaLoose_ImpactPoint_GenTk',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/NumberOfGoodPVtx_offline',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/GoodPVtxNumberOfTracks_offline',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/NumberofTracks_Hardvtx_PUvtx_GenTk',
        'Tracking/PrimaryVertices/highPurityTracks/pt_0to1/offline/FractionOfGoodPVtx_offline',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_Ratio_byFoldingmap_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_Ratio_byFoldingmap_op_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_RelativeDifference_byFoldingmap_ImpactPoint_GenTk',
        'Tracking/TrackParameters/generalTracks/GeneralProperties/TkEtaPhi_RelativeDifference_byFoldingmap_op_ImpactPoint_GenTk',
        'OfflinePV/offlinePrimaryVertices/tagVtxProb',
        'OfflinePV/offlinePrimaryVertices/tagType',
        'OfflinePV/Resolution/PV/pull_x',
        'OfflinePV/Resolution/PV/pull_y',
        'OfflinePV/Resolution/PV/pull_z',
        'OfflinePV/offlinePrimaryVertices/tagDiffX',
        'OfflinePV/offlinePrimaryVertices/tagDiffY',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_highPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_highPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_mediumPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_mediumPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_lowPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/CHFrac_lowPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_highPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_highPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_mediumPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_mediumPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_lowPt_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/ChMultiplicity_lowPt_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Constituents',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Eta',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Eta_uncor',
        'JetMET/Jet/Cleanedak4PFJetsCHS/JetEnergyCorr',
        'JetMET/Jet/Cleanedak4PFJetsCHS/NJets',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Phi_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsCHS/Pt',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/PtJetMET/Jet/Cleanedak4PFJetsPuppi/Phi',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Phi_Barrel',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Phi_EndCap',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/JetEnergyCorr',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/NJets',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Eta',
        'JetMET/Jet/Cleanedak4PFJetsPuppi/Eta_uncor',
        'JetMET/MET/pfMETT1/Cleaned/METSig',
        'JetMET/vertices',
        'JetMET/HIJetValidation/akCs4PFJets/SumPFPt',
        'JetMET/HIJetValidation/akCs4PFJets/NJets',
        'JetMET/HIJetValidation/akCs4PFJets/NPFpart',
        'JetMET/HIJetValidation/akPu4CaloJets/SumCaloPt',
        'JetMET/HIJetValidation/akPu4CaloJets/NCalopart',
        'JetMET/HIJetValidation/akPu4CaloJets/NJets',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_pt',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_eta',
        'Muons/MuonRecoAnalyzer/GlbMuon_Glb_phi',
        'Muons/MuonRecoAnalyzer/Res_TkGlb_qOverlap',
        'Muons/diMuonHistograms/GlbGlbMuon_LM',
        'Muons/diMuonHistograms/GlbGlbMuon_HM',
        'Muons/Isolation/global/relPFIso_R03',
        'Muons/globalMuons/GeneralProperties/NumberOfMeanRecHitsPerTrack_glb',
        'Muons/standAloneMuonsUpdatedAtVtx/HitProperties/NumberOfValidRecHitsPerTrack_sta',
        'Muons/MuonRecoOneHLT/GlbMuon_Glb_pt',
        'Muons/MuonRecoOneHLT/GlbMuon_Glb_eta',
        'Egamma/Electrons/Ele5_TagAndProbe/ele0_vertexPt_barrel',
        'Egamma/Electrons/Ele5_TagAndProbe/ele1_vertexPt_endcaps',
        'Egamma/Electrons/Ele5_TagAndProbe/ele2_vertexEta',
        'Egamma/Electrons/Ele5_TagAndProbe/ele5_vertexZ',
        'Egamma/Electrons/Ele5_TagAndProbe/ele10_Eop_barrel',
        'Egamma/Electrons/Ele5_TagAndProbe/ele10_Eop_endcaps',
        'Egamma/Electrons/Ele5_TagAndProbe/ele101_etaEff',
        'Egamma/Electrons/Ele5_TagAndProbe/ele102_phiEff',
        'Egamma/Electrons/Ele5_TagAndProbe/ele201_mee_os'
     ) ),
    assertLegacySafe = cms.untracked.bool(False),
    enableMultiThread = cms.untracked.bool(True),
    onlineMode = cms.untracked.bool(False),
    saveByLumi = cms.untracked.bool(False),
    trackME = cms.untracked.string(''),
    verbose = cms.untracked.int32(0)
)


process.MessageLogger = cms.Service("MessageLogger",
    cerr = cms.untracked.PSet(
        FwkReport = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000),
            reportEvery = cms.untracked.int32(100)
        ),
        FwkSummary = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000),
            reportEvery = cms.untracked.int32(1)
        ),
        INFO = cms.untracked.PSet(
            limit = cms.untracked.int32(0)
        ),
        Root_NoDictionary = cms.untracked.PSet(
            limit = cms.untracked.int32(0)
        ),
        default = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000)
        ),
        enable = cms.untracked.bool(True),
        enableStatistics = cms.untracked.bool(False),
        lineLength = cms.optional.untracked.int32,
        noLineBreaks = cms.optional.untracked.bool,
        noTimeStamps = cms.untracked.bool(False),
        resetStatistics = cms.untracked.bool(False),
        statisticsThreshold = cms.untracked.string('WARNING'),
        threshold = cms.untracked.string('INFO'),
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    cout = cms.untracked.PSet(
        enable = cms.untracked.bool(False),
        enableStatistics = cms.untracked.bool(False),
        lineLength = cms.optional.untracked.int32,
        noLineBreaks = cms.optional.untracked.bool,
        noTimeStamps = cms.optional.untracked.bool,
        resetStatistics = cms.untracked.bool(False),
        statisticsThreshold = cms.optional.untracked.string,
        threshold = cms.optional.untracked.string,
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    debugModules = cms.untracked.vstring(),
    default = cms.untracked.PSet(
        limit = cms.optional.untracked.int32,
        lineLength = cms.untracked.int32(80),
        noLineBreaks = cms.untracked.bool(False),
        noTimeStamps = cms.untracked.bool(False),
        reportEvery = cms.untracked.int32(1),
        statisticsThreshold = cms.untracked.string('INFO'),
        threshold = cms.untracked.string('INFO'),
        timespan = cms.optional.untracked.int32,
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    files = cms.untracked.PSet(
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            enableStatistics = cms.untracked.bool(False),
            extension = cms.optional.untracked.string,
            filename = cms.optional.untracked.string,
            lineLength = cms.optional.untracked.int32,
            noLineBreaks = cms.optional.untracked.bool,
            noTimeStamps = cms.optional.untracked.bool,
            output = cms.optional.untracked.string,
            resetStatistics = cms.untracked.bool(False),
            statisticsThreshold = cms.optional.untracked.string,
            threshold = cms.optional.untracked.string,
            allowAnyLabel_=cms.optional.untracked.PSetTemplate(
                limit = cms.optional.untracked.int32,
                reportEvery = cms.untracked.int32(1),
                timespan = cms.optional.untracked.int32
            )
        )
    ),
    suppressDebug = cms.untracked.vstring(),
    suppressFwkInfo = cms.untracked.vstring(),
    suppressInfo = cms.untracked.vstring(),
    suppressWarning = cms.untracked.vstring(),
    allowAnyLabel_=cms.optional.untracked.PSetTemplate(
        limit = cms.optional.untracked.int32,
        reportEvery = cms.untracked.int32(1),
        timespan = cms.optional.untracked.int32
    )
)


process.RandomNumberGeneratorService = cms.Service("RandomNumberGeneratorService",
    CTPPSFastRecHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(1357987)
    ),
    LHCTransport = cms.PSet(
        engineName = cms.untracked.string('TRandom3'),
        initialSeed = cms.untracked.uint32(87654321)
    ),
    MuonSimHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(987346)
    ),
    RPSiDetDigitizer = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(137137)
    ),
    RPixDetDigitizer = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(137137)
    ),
    VtxSmeared = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(98765432)
    ),
    ecalPreshowerRecHit = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(6541321)
    ),
    ecalRecHit = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(654321)
    ),
    externalLHEProducer = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(234567)
    ),
    famosPileUp = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(918273)
    ),
    fastSimProducer = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(13579)
    ),
    fastTrackerRecHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(24680)
    ),
    g4SimHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(11)
    ),
    generator = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(123456789)
    ),
    hbhereco = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(541321)
    ),
    hfreco = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(541321)
    ),
    hiSignal = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(123456789)
    ),
    hiSignalG4SimHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(11)
    ),
    hiSignalLHCTransport = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(88776655)
    ),
    horeco = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(541321)
    ),
    l1ParamMuons = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(6453209)
    ),
    mix = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(12345)
    ),
    mixData = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(12345)
    ),
    mixGenPU = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(918273)
    ),
    mixRecoTracks = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(918273)
    ),
    mixSimCaloHits = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(918273)
    ),
    paramMuons = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(54525)
    ),
    saveFileName = cms.untracked.string(''),
    simBeamSpotFilter = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(87654321)
    ),
    simMuonCSCDigis = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(11223344)
    ),
    simMuonDTDigis = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(1234567)
    ),
    simMuonRPCDigis = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(1234567)
    ),
    simSiStripDigiSimLink = cms.PSet(
        engineName = cms.untracked.string('MixMaxRng'),
        initialSeed = cms.untracked.uint32(1234567)
    )
)


process.CSCGeometryESModule = cms.ESProducer("CSCGeometryESModule",
    alignmentsLabel = cms.string(''),
    appendToDataLabel = cms.string(''),
    applyAlignment = cms.bool(True),
    debugV = cms.untracked.bool(False),
    fromDD4hep = cms.bool(False),
    fromDDD = cms.bool(False),
    useCentreTIOffsets = cms.bool(False),
    useGangedStripsInME1a = cms.bool(True),
    useOnlyWiresInME1a = cms.bool(False),
    useRealWireGeometry = cms.bool(True)
)


process.CaloGeometryBuilder = cms.ESProducer("CaloGeometryBuilder",
    SelectedCalos = cms.vstring(
        'HCAL',
        'ZDC',
        'CASTOR',
        'EcalBarrel',
        'EcalEndcap',
        'EcalPreshower',
        'TOWER'
    )
)


process.CaloTopologyBuilder = cms.ESProducer("CaloTopologyBuilder")


process.CaloTowerGeometryFromDBEP = cms.ESProducer("CaloTowerGeometryFromDBEP",
    applyAlignment = cms.bool(False)
)


process.CaloTowerTopologyEP = cms.ESProducer("CaloTowerTopologyEP",
    appendToDataLabel = cms.string('')
)


process.CastorDbProducer = cms.ESProducer("CastorDbProducer",
    appendToDataLabel = cms.string(''),
    dump = cms.untracked.vstring(),
    file = cms.untracked.string('')
)


process.CastorGeometryFromDBEP = cms.ESProducer("CastorGeometryFromDBEP",
    applyAlignment = cms.bool(False)
)


process.DTGeometryESModule = cms.ESProducer("DTGeometryESModule",
    DDDetector = cms.ESInputTag("",""),
    alignmentsLabel = cms.string(''),
    appendToDataLabel = cms.string(''),
    applyAlignment = cms.bool(True),
    attribute = cms.string('MuStructure'),
    fromDD4hep = cms.bool(False),
    fromDDD = cms.bool(False),
    value = cms.string('MuonBarrelDT')
)


process.EcalBarrelGeometryFromDBEP = cms.ESProducer("EcalBarrelGeometryFromDBEP",
    applyAlignment = cms.bool(True)
)


process.EcalElectronicsMappingBuilder = cms.ESProducer("EcalElectronicsMappingBuilder")


process.EcalEndcapGeometryFromDBEP = cms.ESProducer("EcalEndcapGeometryFromDBEP",
    applyAlignment = cms.bool(True)
)


process.EcalLaserCorrectionService = cms.ESProducer("EcalLaserCorrectionService",
    maxExtrapolationTimeInSec = cms.uint32(0)
)


process.EcalLaserCorrectionServiceMC = cms.ESProducer("EcalLaserCorrectionServiceMC",
    appendToDataLabel = cms.string('')
)


process.EcalPreshowerGeometryFromDBEP = cms.ESProducer("EcalPreshowerGeometryFromDBEP",
    applyAlignment = cms.bool(True)
)


process.EcalTrigTowerConstituentsMapBuilder = cms.ESProducer("EcalTrigTowerConstituentsMapBuilder",
    MapFile = cms.untracked.string('Geometry/EcalMapping/data/EndCap_TTMap.txt')
)


process.GlobalTrackingGeometryESProducer = cms.ESProducer("GlobalTrackingGeometryESProducer")


process.HcalAlignmentEP = cms.ESProducer("HcalAlignmentEP")


process.HcalGeometryFromDBEP = cms.ESProducer("HcalGeometryFromDBEP",
    applyAlignment = cms.bool(True)
)


process.MuonDetLayerGeometryESProducer = cms.ESProducer("MuonDetLayerGeometryESProducer")


process.MuonNumberingInitialization = cms.ESProducer("MuonNumberingInitialization")


process.ParabolicParametrizedMagneticFieldProducer = cms.ESProducer("AutoParametrizedMagneticFieldProducer",
    label = cms.untracked.string('ParabolicMf'),
    valueOverride = cms.int32(-1),
    version = cms.string('Parabolic')
)


process.RPCGeometryESModule = cms.ESProducer("RPCGeometryESModule",
    fromDD4hep = cms.untracked.bool(False),
    fromDDD = cms.untracked.bool(False)
)


process.SiStripRecHitMatcherESProducer = cms.ESProducer("SiStripRecHitMatcherESProducer",
    ComponentName = cms.string('StandardMatcher'),
    NSigmaInside = cms.double(3.0),
    PreFilter = cms.bool(False)
)


process.StripCPEfromTrackAngleESProducer = cms.ESProducer("StripCPEESProducer",
    ComponentName = cms.string('StripCPEfromTrackAngle'),
    ComponentType = cms.string('StripCPEfromTrackAngle'),
    parameters = cms.PSet(
        mLC_P0 = cms.double(-0.326),
        mLC_P1 = cms.double(0.618),
        mLC_P2 = cms.double(0.3),
        mTEC_P0 = cms.double(-1.885),
        mTEC_P1 = cms.double(0.471),
        mTIB_P0 = cms.double(-0.742),
        mTIB_P1 = cms.double(0.202),
        mTID_P0 = cms.double(-1.427),
        mTID_P1 = cms.double(0.433),
        mTOB_P0 = cms.double(-1.026),
        mTOB_P1 = cms.double(0.253),
        maxChgOneMIP = cms.double(6000.0),
        useLegacyError = cms.bool(False)
    )
)


process.TrackerAdditionalParametersPerDet = cms.ESProducer("TrackerAdditionalParametersPerDetESModule",
    appendToDataLabel = cms.string('')
)


process.TrackerRecoGeometryESProducer = cms.ESProducer("TrackerRecoGeometryESProducer",
    usePhase2Stacks = cms.bool(False)
)


process.VolumeBasedMagneticFieldESProducer = cms.ESProducer("VolumeBasedMagneticFieldESProducerFromDB",
    debugBuilder = cms.untracked.bool(False),
    label = cms.untracked.string(''),
    valueOverride = cms.int32(-1)
)


process.XMLFromDBSource = cms.ESProducer("XMLIdealGeometryESProducer",
    label = cms.string('Extended'),
    rootDDName = cms.string('cms:OCMS')
)


process.ZdcGeometryFromDBEP = cms.ESProducer("ZdcGeometryFromDBEP",
    applyAlignment = cms.bool(False)
)


process.caloSimulationParameters = cms.ESProducer("CaloSimParametersESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False)
)


process.ctppsBeamParametersFromLHCInfoESSource = cms.ESProducer("CTPPSBeamParametersFromLHCInfoESSource",
    appendToDataLabel = cms.string(''),
    beamDivX45 = cms.double(0.1),
    beamDivX56 = cms.double(0.1),
    beamDivY45 = cms.double(0.1),
    beamDivY56 = cms.double(0.1),
    lhcInfoLabel = cms.string(''),
    lhcInfoPerFillLabel = cms.string(''),
    lhcInfoPerLSLabel = cms.string(''),
    useNewLHCInfo = cms.bool(False),
    vtxOffsetX45 = cms.double(0.01),
    vtxOffsetX56 = cms.double(0.01),
    vtxOffsetY45 = cms.double(0.01),
    vtxOffsetY56 = cms.double(0.01),
    vtxOffsetZ45 = cms.double(0.01),
    vtxOffsetZ56 = cms.double(0.01),
    vtxStddevX = cms.double(0.02),
    vtxStddevY = cms.double(0.02),
    vtxStddevZ = cms.double(0.02)
)


process.ctppsInterpolatedOpticalFunctionsESSource = cms.ESProducer("CTPPSInterpolatedOpticalFunctionsESSource",
    appendToDataLabel = cms.string(''),
    lhcInfoLabel = cms.string(''),
    lhcInfoPerFillLabel = cms.string(''),
    lhcInfoPerLSLabel = cms.string(''),
    opticsLabel = cms.string(''),
    useNewLHCInfo = cms.bool(False)
)


process.ecalSimulationParametersEB = cms.ESProducer("EcalSimParametersESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False),
    name = cms.string('EcalHitsEB')
)


process.ecalSimulationParametersEE = cms.ESProducer("EcalSimParametersESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False),
    name = cms.string('EcalHitsEE')
)


process.ecalSimulationParametersES = cms.ESProducer("EcalSimParametersESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False),
    name = cms.string('EcalHitsES')
)


process.fakeForIdealAlignment = cms.ESProducer("FakeAlignmentProducer",
    appendToDataLabel = cms.string('fakeForIdeal')
)


process.hcalDDDRecConstants = cms.ESProducer("HcalDDDRecConstantsESModule",
    appendToDataLabel = cms.string('')
)


process.hcalDDDSimConstants = cms.ESProducer("HcalDDDSimConstantsESModule",
    appendToDataLabel = cms.string('')
)


process.hcalSimulationConstants = cms.ESProducer("HcalSimulationConstantsESModule",
    appendToDataLabel = cms.string('')
)


process.hcalSimulationParameters = cms.ESProducer("HcalSimParametersESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False)
)


process.hcalTopologyIdeal = cms.ESProducer("HcalTopologyIdealEP",
    Exclude = cms.untracked.string(''),
    MergePosition = cms.untracked.bool(False),
    appendToDataLabel = cms.string('')
)


process.hcal_db_producer = cms.ESProducer("HcalDbProducer",
    dump = cms.untracked.vstring(''),
    file = cms.untracked.string('')
)


process.idealForDigiCSCGeometry = cms.ESProducer("CSCGeometryESModule",
    alignmentsLabel = cms.string('fakeForIdeal'),
    appendToDataLabel = cms.string('idealForDigi'),
    applyAlignment = cms.bool(False),
    debugV = cms.untracked.bool(False),
    fromDD4hep = cms.bool(False),
    fromDDD = cms.bool(False),
    useCentreTIOffsets = cms.bool(False),
    useGangedStripsInME1a = cms.bool(True),
    useOnlyWiresInME1a = cms.bool(False),
    useRealWireGeometry = cms.bool(True)
)


process.idealForDigiDTGeometry = cms.ESProducer("DTGeometryESModule",
    DDDetector = cms.ESInputTag("",""),
    alignmentsLabel = cms.string('fakeForIdeal'),
    appendToDataLabel = cms.string('idealForDigi'),
    applyAlignment = cms.bool(False),
    attribute = cms.string('MuStructure'),
    fromDD4hep = cms.bool(False),
    fromDDD = cms.bool(False),
    value = cms.string('MuonBarrelDT')
)


process.idealForDigiTrackerGeometry = cms.ESProducer("TrackerDigiGeometryESModule",
    alignmentsLabel = cms.string('fakeForIdeal'),
    appendToDataLabel = cms.string('idealForDigi'),
    applyAlignment = cms.bool(False),
    fromDDD = cms.bool(False)
)


process.multipleScatteringParametrisationMakerESProducer = cms.ESProducer("MultipleScatteringParametrisationMakerESProducer",
    appendToDataLabel = cms.string('')
)


process.muonGeometryConstants = cms.ESProducer("MuonGeometryConstantsESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False)
)


process.muonOffsetESProducer = cms.ESProducer("MuonOffsetESProducer",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False),
    names = cms.vstring(
        'MuonCommonNumbering',
        'MuonBarrel',
        'MuonEndcap',
        'MuonBarrelWheels',
        'MuonBarrelStation1',
        'MuonBarrelStation2',
        'MuonBarrelStation3',
        'MuonBarrelStation4',
        'MuonBarrelSuperLayer',
        'MuonBarrelLayer',
        'MuonBarrelWire',
        'MuonRpcPlane1I',
        'MuonRpcPlane1O',
        'MuonRpcPlane2I',
        'MuonRpcPlane2O',
        'MuonRpcPlane3S',
        'MuonRpcPlane4',
        'MuonRpcChamberLeft',
        'MuonRpcChamberMiddle',
        'MuonRpcChamberRight',
        'MuonRpcEndcap1',
        'MuonRpcEndcap2',
        'MuonRpcEndcap3',
        'MuonRpcEndcap4',
        'MuonRpcEndcapSector',
        'MuonRpcEndcapChamberB1',
        'MuonRpcEndcapChamberB2',
        'MuonRpcEndcapChamberB3',
        'MuonRpcEndcapChamberC1',
        'MuonRpcEndcapChamberC2',
        'MuonRpcEndcapChamberC3',
        'MuonRpcEndcapChamberE1',
        'MuonRpcEndcapChamberE2',
        'MuonRpcEndcapChamberE3',
        'MuonRpcEndcapChamberF1',
        'MuonRpcEndcapChamberF2',
        'MuonRpcEndcapChamberF3',
        'MuonEndcapStation1',
        'MuonEndcapStation2',
        'MuonEndcapStation3',
        'MuonEndcapStation4',
        'MuonEndcapSubrings',
        'MuonEndcapSectors',
        'MuonEndcapLayers',
        'MuonEndcapRing1',
        'MuonEndcapRing2',
        'MuonEndcapRing3',
        'MuonEndcapRingA',
        'MuonGEMEndcap',
        'MuonGEMSector',
        'MuonGEMChamber'
    )
)


process.siPixelQualityESProducer = cms.ESProducer("SiPixelQualityESProducer",
    ListOfRecordToMerge = cms.VPSet(
        cms.PSet(
            record = cms.string('SiPixelQualityFromDbRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiPixelDetVOffRcd'),
            tag = cms.string('')
        )
    ),
    appendToDataLabel = cms.string(''),
    siPixelQualityFromDbLabel = cms.string('')
)


process.siStripBackPlaneCorrectionDepESProducer = cms.ESProducer("SiStripBackPlaneCorrectionDepESProducer",
    BackPlaneCorrectionDeconvMode = cms.PSet(
        label = cms.untracked.string('deconvolution'),
        record = cms.string('SiStripBackPlaneCorrectionRcd')
    ),
    BackPlaneCorrectionPeakMode = cms.PSet(
        label = cms.untracked.string('peak'),
        record = cms.string('SiStripBackPlaneCorrectionRcd')
    ),
    LatencyRecord = cms.PSet(
        label = cms.untracked.string(''),
        record = cms.string('SiStripLatencyRcd')
    )
)


process.siStripGainESProducer = cms.ESProducer("SiStripGainESProducer",
    APVGain = cms.VPSet(
        cms.PSet(
            Label = cms.untracked.string(''),
            NormalizationFactor = cms.untracked.double(1.0),
            Record = cms.string('SiStripApvGainRcd')
        ),
        cms.PSet(
            Label = cms.untracked.string(''),
            NormalizationFactor = cms.untracked.double(1.0),
            Record = cms.string('SiStripApvGain2Rcd')
        )
    ),
    AutomaticNormalization = cms.bool(False),
    appendToDataLabel = cms.string(''),
    printDebug = cms.untracked.bool(False)
)


process.siStripLorentzAngleDepESProducer = cms.ESProducer("SiStripLorentzAngleDepESProducer",
    LatencyRecord = cms.PSet(
        label = cms.untracked.string(''),
        record = cms.string('SiStripLatencyRcd')
    ),
    LorentzAngleDeconvMode = cms.PSet(
        label = cms.untracked.string('deconvolution'),
        record = cms.string('SiStripLorentzAngleRcd')
    ),
    LorentzAnglePeakMode = cms.PSet(
        label = cms.untracked.string('peak'),
        record = cms.string('SiStripLorentzAngleRcd')
    )
)


process.siStripQualityESProducer = cms.ESProducer("SiStripQualityESProducer",
    ListOfRecordToMerge = cms.VPSet(
        cms.PSet(
            record = cms.string('SiStripDetVOffRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiStripDetCablingRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('RunInfoRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiStripBadChannelRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiStripBadFiberRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiStripBadModuleRcd'),
            tag = cms.string('')
        ),
        cms.PSet(
            record = cms.string('SiStripBadStripRcd'),
            tag = cms.string('')
        )
    ),
    PrintDebugOutput = cms.bool(False),
    ReduceGranularity = cms.bool(False),
    ThresholdForReducedGranularity = cms.double(0.3),
    UseEmptyRunInfo = cms.bool(False),
    appendToDataLabel = cms.string('')
)


process.sistripconn = cms.ESProducer("SiStripConnectivity")


process.stripCPEESProducer = cms.ESProducer("StripCPEESProducer",
    ComponentName = cms.string('stripCPE'),
    ComponentType = cms.string('SimpleStripCPE'),
    parameters = cms.PSet(

    )
)


process.trackerGeometryDB = cms.ESProducer("TrackerDigiGeometryESModule",
    alignmentsLabel = cms.string(''),
    appendToDataLabel = cms.string(''),
    applyAlignment = cms.bool(True),
    fromDDD = cms.bool(False)
)


process.trackerNumberingGeometryDB = cms.ESProducer("TrackerGeometricDetESModule",
    appendToDataLabel = cms.string(''),
    fromDD4hep = cms.bool(False),
    fromDDD = cms.bool(False)
)


process.trackerTopology = cms.ESProducer("TrackerTopologyEP",
    appendToDataLabel = cms.string('')
)


process.zdcTopologyEP = cms.ESProducer("ZdcTopologyEP",
    appendToDataLabel = cms.string('')
)


process.GlobalTag = cms.ESSource("PoolDBESSource",
    DBParameters = cms.PSet(
        authenticationPath = cms.untracked.string(''),
        authenticationSystem = cms.untracked.int32(0),
        connectionTimeout = cms.untracked.int32(0),
        messageLevel = cms.untracked.int32(0),
        security = cms.untracked.string('')
    ),
    DumpStat = cms.untracked.bool(False),
    JsonDumpFileName = cms.untracked.string(''),
    ReconnectEachRun = cms.untracked.bool(False),
    RefreshAlways = cms.untracked.bool(False),
    RefreshEachRun = cms.untracked.bool(False),
    RefreshOpenIOVs = cms.untracked.bool(False),
    appendToDataLabel = cms.string(''),
    connect = cms.string('frontier://FrontierProd/CMS_CONDITIONS'),
    frontierKey = cms.untracked.string(''),
    globaltag = cms.string('142X_mcRun3_2025_realistic_v7'),
    pfnPostfix = cms.untracked.string(''),
    pfnPrefix = cms.untracked.string(''),
    recordsToDebug = cms.untracked.vstring(),
    snapshotTime = cms.string(''),
    toGet = cms.VPSet()
)


process.HcalTimeSlewEP = cms.ESSource("HcalTimeSlewEP",
    appendToDataLabel = cms.string('HBHE'),
    timeSlewParametersM2 = cms.VPSet(
        cms.PSet(
            slope = cms.double(-3.178648),
            tmax = cms.double(16.0),
            tzero = cms.double(23.960177)
        ),
        cms.PSet(
            slope = cms.double(-1.5610227),
            tmax = cms.double(10.0),
            tzero = cms.double(11.977461)
        ),
        cms.PSet(
            slope = cms.double(-1.075824),
            tmax = cms.double(6.25),
            tzero = cms.double(9.109694)
        )
    ),
    timeSlewParametersM3 = cms.VPSet(
        cms.PSet(
            cap = cms.double(6.0),
            tspar0 = cms.double(12.2999),
            tspar0_siPM = cms.double(0.0),
            tspar1 = cms.double(-2.19142),
            tspar1_siPM = cms.double(0.0),
            tspar2 = cms.double(0.0),
            tspar2_siPM = cms.double(0.0)
        ),
        cms.PSet(
            cap = cms.double(6.0),
            tspar0 = cms.double(15.5),
            tspar0_siPM = cms.double(0.0),
            tspar1 = cms.double(-3.2),
            tspar1_siPM = cms.double(0.0),
            tspar2 = cms.double(32.0),
            tspar2_siPM = cms.double(0.0)
        ),
        cms.PSet(
            cap = cms.double(6.0),
            tspar0 = cms.double(12.2999),
            tspar0_siPM = cms.double(0.0),
            tspar1 = cms.double(-2.19142),
            tspar1_siPM = cms.double(0.0),
            tspar2 = cms.double(0.0),
            tspar2_siPM = cms.double(0.0)
        ),
        cms.PSet(
            cap = cms.double(6.0),
            tspar0 = cms.double(12.2999),
            tspar0_siPM = cms.double(0.0),
            tspar1 = cms.double(-2.19142),
            tspar1_siPM = cms.double(0.0),
            tspar2 = cms.double(0.0),
            tspar2_siPM = cms.double(0.0)
        )
    )
)


process.HepPDTESSource = cms.ESSource("HepPDTESSource",
    pdtFileName = cms.FileInPath('SimGeneral/HepPDTESSource/data/pythiaparticle.tbl')
)


process.eegeom = cms.ESSource("EmptyESSource",
    firstValid = cms.vuint32(1),
    iovIsRunNotTime = cms.bool(True),
    recordName = cms.string('EcalMappingRcd')
)


process.es_hardcode = cms.ESSource("HcalHardcodeCalibrations",
    GainWidthsForTrigPrims = cms.bool(False),
    HBRecalibration = cms.bool(False),
    HBmeanenergies = cms.FileInPath('CalibCalorimetry/HcalPlugins/data/meanenergiesHB.txt'),
    HBreCalibCutoff = cms.double(20.0),
    HERecalibration = cms.bool(False),
    HEmeanenergies = cms.FileInPath('CalibCalorimetry/HcalPlugins/data/meanenergiesHE.txt'),
    HEreCalibCutoff = cms.double(20.0),
    HFRecalParameterBlock = cms.PSet(
        HFdepthOneParameterA = cms.vdouble(
            0.004123, 0.00602, 0.008201, 0.010489, 0.013379,
            0.016997, 0.021464, 0.027371, 0.034195, 0.044807,
            0.058939, 0.125497
        ),
        HFdepthOneParameterB = cms.vdouble(
            -4e-06, -2e-06, 0.0, 4e-06, 1.5e-05,
            2.6e-05, 6.3e-05, 8.4e-05, 0.00016, 0.000107,
            0.000425, 0.000209
        ),
        HFdepthTwoParameterA = cms.vdouble(
            0.002861, 0.004168, 0.0064, 0.008388, 0.011601,
            0.014425, 0.018633, 0.023232, 0.028274, 0.035447,
            0.051579, 0.086593
        ),
        HFdepthTwoParameterB = cms.vdouble(
            -2e-06, -0.0, -7e-06, -6e-06, -2e-06,
            1e-06, 1.9e-05, 3.1e-05, 6.7e-05, 1.2e-05,
            0.000157, -3e-06
        )
    ),
    HFRecalibration = cms.bool(False),
    SiPMCharacteristics = cms.VPSet(
        cms.PSet(
            crosstalk = cms.double(0.0),
            nonlin1 = cms.double(1.0),
            nonlin2 = cms.double(0.0),
            nonlin3 = cms.double(0.0),
            pixels = cms.int32(36000)
        ),
        cms.PSet(
            crosstalk = cms.double(0.0),
            nonlin1 = cms.double(1.0),
            nonlin2 = cms.double(0.0),
            nonlin3 = cms.double(0.0),
            pixels = cms.int32(2500)
        ),
        cms.PSet(
            crosstalk = cms.double(0.17),
            nonlin1 = cms.double(1.00985),
            nonlin2 = cms.double(7.84089e-06),
            nonlin3 = cms.double(2.86282e-10),
            pixels = cms.int32(27370)
        ),
        cms.PSet(
            crosstalk = cms.double(0.196),
            nonlin1 = cms.double(1.00546),
            nonlin2 = cms.double(6.40239e-06),
            nonlin3 = cms.double(1.27011e-10),
            pixels = cms.int32(38018)
        ),
        cms.PSet(
            crosstalk = cms.double(0.17),
            nonlin1 = cms.double(1.00985),
            nonlin2 = cms.double(7.84089e-06),
            nonlin3 = cms.double(2.86282e-10),
            pixels = cms.int32(27370)
        ),
        cms.PSet(
            crosstalk = cms.double(0.196),
            nonlin1 = cms.double(1.00546),
            nonlin2 = cms.double(6.40239e-06),
            nonlin3 = cms.double(1.27011e-10),
            pixels = cms.int32(38018)
        ),
        cms.PSet(
            crosstalk = cms.double(0.0),
            nonlin1 = cms.double(1.0),
            nonlin2 = cms.double(0.0),
            nonlin3 = cms.double(0.0),
            pixels = cms.int32(0)
        )
    ),
    hb = cms.PSet(
        darkCurrent = cms.vdouble(0.0),
        doRadiationDamage = cms.bool(False),
        gain = cms.vdouble(0.19),
        gainWidth = cms.vdouble(0.0),
        mcShape = cms.int32(125),
        noiseCorrelation = cms.vdouble(0.0),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(3.285),
        pedestalWidth = cms.double(0.809),
        photoelectronsToAnalog = cms.double(0.3305),
        qieOffset = cms.vdouble(-0.49, 1.8, 7.2, 37.9),
        qieSlope = cms.vdouble(0.912, 0.917, 0.922, 0.923),
        qieType = cms.int32(0),
        recoShape = cms.int32(105),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(8)
    ),
    hbUpgrade = cms.PSet(
        darkCurrent = cms.vdouble(0.01, 0.015),
        doRadiationDamage = cms.bool(True),
        gain = cms.vdouble(0.0006252),
        gainWidth = cms.vdouble(0),
        mcShape = cms.int32(206),
        noiseCorrelation = cms.vdouble(0.26, 0.254),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(17.3),
        pedestalWidth = cms.double(1.5),
        photoelectronsToAnalog = cms.double(40.0),
        qieOffset = cms.vdouble(0.0, 0.0, 0.0, 0.0),
        qieSlope = cms.vdouble(0.05376, 0.05376, 0.05376, 0.05376),
        qieType = cms.int32(2),
        radiationDamage = cms.PSet(
            depVsNeutrons = cms.vdouble(5.543e-10, 8.012e-10),
            depVsTemp = cms.double(0.0631),
            intlumiOffset = cms.double(150),
            intlumiToNeutrons = cms.double(367000000.0),
            temperatureBase = cms.double(20),
            temperatureNew = cms.double(-5)
        ),
        recoShape = cms.int32(208),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(16)
    ),
    he = cms.PSet(
        darkCurrent = cms.vdouble(0.0),
        doRadiationDamage = cms.bool(False),
        gain = cms.vdouble(0.23),
        gainWidth = cms.vdouble(0),
        mcShape = cms.int32(125),
        noiseCorrelation = cms.vdouble(0.0),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(3.163),
        pedestalWidth = cms.double(0.9698),
        photoelectronsToAnalog = cms.double(0.3305),
        qieOffset = cms.vdouble(-0.38, 2.0, 7.6, 39.6),
        qieSlope = cms.vdouble(0.912, 0.916, 0.92, 0.922),
        qieType = cms.int32(0),
        recoShape = cms.int32(105),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(9)
    ),
    heUpgrade = cms.PSet(
        darkCurrent = cms.vdouble(0.01, 0.015),
        doRadiationDamage = cms.bool(True),
        gain = cms.vdouble(0.0006252),
        gainWidth = cms.vdouble(0),
        mcShape = cms.int32(206),
        noiseCorrelation = cms.vdouble(0.26, 0.254),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(17.3),
        pedestalWidth = cms.double(1.5),
        photoelectronsToAnalog = cms.double(40.0),
        qieOffset = cms.vdouble(0.0, 0.0, 0.0, 0.0),
        qieSlope = cms.vdouble(0.05376, 0.05376, 0.05376, 0.05376),
        qieType = cms.int32(2),
        radiationDamage = cms.PSet(
            depVsNeutrons = cms.vdouble(5.543e-10, 8.012e-10),
            depVsTemp = cms.double(0.0631),
            intlumiOffset = cms.double(75),
            intlumiToNeutrons = cms.double(29200000.0),
            temperatureBase = cms.double(20),
            temperatureNew = cms.double(5)
        ),
        recoShape = cms.int32(208),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(16)
    ),
    hf = cms.PSet(
        darkCurrent = cms.vdouble(0.0),
        doRadiationDamage = cms.bool(False),
        gain = cms.vdouble(0.14, 0.135),
        gainWidth = cms.vdouble(0.0, 0.0),
        mcShape = cms.int32(301),
        noiseCorrelation = cms.vdouble(0.0),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(9.354),
        pedestalWidth = cms.double(2.516),
        photoelectronsToAnalog = cms.double(0.0),
        qieOffset = cms.vdouble(-0.87, 1.4, 7.8, -29.6),
        qieSlope = cms.vdouble(0.359, 0.358, 0.36, 0.367),
        qieType = cms.int32(0),
        recoShape = cms.int32(301),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(-9999)
    ),
    hfUpgrade = cms.PSet(
        darkCurrent = cms.vdouble(0.0),
        doRadiationDamage = cms.bool(False),
        gain = cms.vdouble(0.14, 0.135),
        gainWidth = cms.vdouble(0.0, 0.0),
        mcShape = cms.int32(301),
        noiseCorrelation = cms.vdouble(0.0),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(13.33),
        pedestalWidth = cms.double(3.33),
        photoelectronsToAnalog = cms.double(0.0),
        qieOffset = cms.vdouble(0.0697, -0.7405, 12.38, -671.9),
        qieSlope = cms.vdouble(0.297, 0.298, 0.298, 0.313),
        qieType = cms.int32(1),
        recoShape = cms.int32(301),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(-9999)
    ),
    ho = cms.PSet(
        darkCurrent = cms.vdouble(0.0),
        doRadiationDamage = cms.bool(False),
        gain = cms.vdouble(0.006, 0.0087),
        gainWidth = cms.vdouble(0.0, 0.0),
        mcShape = cms.int32(201),
        noiseCorrelation = cms.vdouble(0.0),
        noiseThreshold = cms.double(0.0),
        pedestal = cms.double(12.06),
        pedestalWidth = cms.double(0.6285),
        photoelectronsToAnalog = cms.double(4.0),
        qieOffset = cms.vdouble(-0.44, 1.4, 7.1, 38.5),
        qieSlope = cms.vdouble(0.907, 0.915, 0.92, 0.921),
        qieType = cms.int32(0),
        recoShape = cms.int32(201),
        seedThreshold = cms.double(0.1),
        zsThreshold = cms.int32(24)
    ),
    iLumi = cms.double(-1.0),
    killHE = cms.bool(False),
    testHEPlan1 = cms.bool(False),
    testHFQIE10 = cms.bool(False),
    toGet = cms.untracked.vstring('GainWidths'),
    useHBUpgrade = cms.bool(False),
    useHEUpgrade = cms.bool(False),
    useHFUpgrade = cms.bool(False),
    useHOUpgrade = cms.bool(True),
    useIeta18depth1 = cms.bool(True),
    useLayer0Weight = cms.bool(False)
)


process.prefer("es_hardcode")

process.picoEventTableTask = cms.Task(process.puTable, process.rhoTable)


process.picoVertexTableTask = cms.Task(process.picoVertexTable)


process.pfRhoStripTableTask = cms.Task(process.pfPuppiRhoStripTable, process.pfRhoStripTable)


process.picoMuonTableTask = cms.Task(process.picoMuonTable)


process.picoElectronTableTask = cms.Task(process.picoElectronTable)


process.picoJetTableTask = cms.Task(process.picoGenJetTable, process.picoJetMCTable, process.picoJetTable)


process.picoMETTableTask = cms.Task(process.picoMETTable, process.picoRawMETTable)


process.picoPFCandTableTask = cms.Task(process.picoPFCandTable)


process.picoTask = cms.Task(process.pfRhoStripTableTask, process.picoElectronTableTask, process.picoEventTableTask, process.picoJetTableTask, process.picoMETTableTask, process.picoMuonTableTask, process.picoPFCandTableTask, process.picoVertexTableTask)


process.picoEventTableSeq = cms.Sequence(process.picoEventTableTask)


process.picoVertexTableSeq = cms.Sequence(process.picoVertexTableTask)


process.pfRhoStripTableSeq = cms.Sequence(process.pfRhoStripTableTask)


process.picoMuonTableSeq = cms.Sequence(process.picoMuonTableTask)


process.picoElectronTableSeq = cms.Sequence(process.picoElectronTableTask)


process.picoJetTableSeq = cms.Sequence(process.picoJetTable+process.picoJetMCTable+process.picoGenJetTable)


process.picoMETTableSeq = cms.Sequence(process.picoMETTableTask)


process.picoPFCandTableSeq = cms.Sequence(process.picoPFCandTableTask)


process.picoSequence = cms.Sequence(process.picoTask)


process.skimSequence = cms.Sequence()


process.p = cms.Path(process.picoSequence)


process.end = cms.EndPath(process.out)


process.schedule = cms.Schedule(*[ process.p, process.end ])
