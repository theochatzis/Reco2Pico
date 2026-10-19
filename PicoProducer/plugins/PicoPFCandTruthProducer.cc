// Attribution of the reconstructed particle-flow candidates to the simulated
// particles of the signal event.
//
//   charged candidates (reco::TrackRef): the TrackingParticle associated to the
//     track (reco->sim map, best quality) -> its first Geant4 track -> SimTrack;
//     the whole candidate energy goes to that particle (method 1);
//   other candidates: through their PF clusters, cell by cell. For every cell
//     the reconstructed energy (rechit x cluster fraction) is attributed to the
//     signal particles in proportion to their sim deposits in that cell, capped
//     by the GeV-equivalent sim energy of the cell, so that pile-up energy on
//     top of a small signal deposit stays unattributed (method 2);
//   the rest of the candidate energy is unattributed (pile-up, noise, fakes).
//
// With the pile-up truth of a classically mixed event (pileupHits set): the
// cap is the in-time sim energy of the cell, signal plus pile-up, and the
// capped energy is shared between the signal particles and the pile-up in
// proportion to their deposits (puFraction); a charged candidate whose
// TrackingParticle belongs to a pile-up interaction is pile-up entirely. What
// is left is then noise, out-of-time pile-up and the calibration residual.
//
// Products:
//   PFCandTruth (instance "candidates")  one row per PFCand row: signalFraction,
//                                         dominant SimTrack and its fraction, method
//   PFCandSim   (instance "shares")       one row per (candidate, SimTrack) share
//   shareCand / shareSimTrack / shareEnergy  flat vectors (particleFlow index,
//                                         SimTrack index, energy) for the jet matching
#include <algorithm>
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "DataFormats/CaloRecHit/interface/CaloCluster.h"
#include "DataFormats/EcalRecHit/interface/EcalRecHitCollections.h"
#include "DataFormats/HcalRecHit/interface/HcalRecHitCollections.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidate.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidateFwd.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlock.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElement.h"
#include "DataFormats/ParticleFlowReco/interface/PFCluster.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "SimDataFormats/Associations/interface/TrackToTrackingParticleAssociator.h"
#include "SimDataFormats/EncodedEventId/interface/EncodedEventId.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/TrackingAnalysis/interface/TrackingParticle.h"

#include "PicoCaloSimHits.h"

class PicoPFCandTruthProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoPFCandTruthProducer(const edm::ParameterSet& cfg)
      : candsToken_(consumes<reco::PFCandidateCollection>(cfg.getParameter<edm::InputTag>("candidates"))),
        tracksToken_(consumes<reco::TrackCollection>(cfg.getParameter<edm::InputTag>("tracks"))),
        recoToSimToken_(consumes<reco::RecoToSimCollection>(cfg.getParameter<edm::InputTag>("association"))),
        simTracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        ebToken_(consumes<EcalRecHitCollection>(cfg.getParameter<edm::InputTag>("ebRecHits"))),
        eeToken_(consumes<EcalRecHitCollection>(cfg.getParameter<edm::InputTag>("eeRecHits"))),
        esToken_(consumes<EcalRecHitCollection>(cfg.getParameter<edm::InputTag>("esRecHits"))),
        hbheToken_(consumes<HBHERecHitCollection>(cfg.getParameter<edm::InputTag>("hbheRecHits"))),
        hfToken_(consumes<HFRecHitCollection>(cfg.getParameter<edm::InputTag>("hfRecHits"))),
        hoToken_(consumes<HORecHitCollection>(cfg.getParameter<edm::InputTag>("hoRecHits"))),
        pileup_(!cfg.getParameter<std::string>("pileupHits").empty()),
        simHits_(cfg, consumesCollector()),
        candMinPt_(cfg.getParameter<double>("candMinPt")),
        minShareFraction_(cfg.getParameter<double>("minShareFraction")) {
    produces<nanoaod::FlatTable>("candidates");
    produces<nanoaod::FlatTable>("shares");
    produces<std::vector<int>>("shareCand");
    produces<std::vector<int>>("shareSimTrack");
    produces<std::vector<float>>("shareEnergy");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("candidates", edm::InputTag("particleFlow"));
    desc.add<edm::InputTag>("tracks", edm::InputTag("generalTracks"));
    desc.add<edm::InputTag>("association", edm::InputTag("picoTrackingParticleRecoTrackAssociation"));
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("ebRecHits", edm::InputTag("ecalRecHit", "EcalRecHitsEB"));
    desc.add<edm::InputTag>("eeRecHits", edm::InputTag("ecalRecHit", "EcalRecHitsEE"));
    desc.add<edm::InputTag>("esRecHits", edm::InputTag("ecalPreshowerRecHit", "EcalRecHitsES"));
    desc.add<edm::InputTag>("hbheRecHits", edm::InputTag("hbhereco"));
    desc.add<edm::InputTag>("hfRecHits", edm::InputTag("hfreco"));
    desc.add<edm::InputTag>("hoRecHits", edm::InputTag("horeco"));
    pico::CaloSimHits::fillDescription(desc);
    desc.add<double>("candMinPt", 0.0);
    desc.add<double>("minShareFraction", 0.01);
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& cands = event.get(candsToken_);
    edm::Handle<reco::TrackCollection> tracks;
    event.getByToken(tracksToken_, tracks);
    const auto& recoToSim = event.get(recoToSimToken_);
    const auto& simTracks = event.get(simTracksToken_);

    std::unordered_map<unsigned int, int> rowOfTrackId;
    for (size_t i = 0; i < simTracks.size(); ++i)
      rowOfTrackId.emplace(simTracks[i].trackId(), static_cast<int>(i));

    // track -> SimTrack through the association map (best quality first); a track whose
    // TrackingParticle belongs to another interaction is pile-up
    std::vector<int> simOfTrack(tracks->size(), -1);
    std::vector<uint8_t> puTrack(tracks->size(), 0);
    for (const auto& entry : recoToSim) {
      const auto& tr = entry.key;
      if (tr.isNull() || tr.id() != tracks.id() || tr.key() >= simOfTrack.size() || entry.val.empty())
        continue;
      const TrackingParticleRef& tp = entry.val.front().first;
      if (tp.isNull() || !tp.isAvailable() || tp->g4Tracks().empty())
        continue;
      const EncodedEventId eid = tp->eventId();
      if (eid.bunchCrossing() != 0 || eid.event() != 0) {
        puTrack[tr.key()] = 1;
        continue;
      }
      auto it = rowOfTrackId.find(tp->g4Tracks().front().trackId());
      if (it != rowOfTrackId.end())
        simOfTrack[tr.key()] = it->second;
    }

    // rechit energies by cell
    std::unordered_map<uint32_t, float> recE;
    for (const auto& tok : {ebToken_, eeToken_, esToken_})
      for (const auto& h : event.get(tok))
        recE[h.id().rawId()] = h.energy();
    for (const auto& h : event.get(hbheToken_))
      recE[h.id().rawId()] = h.energy();
    for (const auto& h : event.get(hfToken_))
      recE[h.id().rawId()] = h.energy();
    for (const auto& h : event.get(hoToken_))
      recE[h.id().rawId()] = h.energy();

    // sim shares by cell (all subdetectors merged: rawIds are unique across them)
    std::map<uint32_t, pico::CellShares> cellsBySub[pico::NSUB];
    simHits_.build(event, setup, rowOfTrackId, cellsBySub);
    std::unordered_map<uint32_t, const pico::CellShares*> cells;
    for (int s = 0; s < pico::NSUB; ++s)
      for (const auto& kv : cellsBySub[s])
        cells[kv.first] = &kv.second;

    auto shareCand = std::make_unique<std::vector<int>>();
    auto shareSim = std::make_unique<std::vector<int>>();
    auto shareE = std::make_unique<std::vector<float>>();
    std::vector<int32_t> cRow, cDominant, cMethod, sCand, sSim;
    std::vector<float> cSignalFrac, cDominantFrac, sEnergy, sFraction, cPUFrac;

    int32_t row = 0;
    for (size_t c = 0; c < cands.size(); ++c) {
      const reco::PFCandidate& cand = cands[c];
      if (cand.pt() < candMinPt_)
        continue;
      std::map<int, double> shares;
      double pu = 0;  // energy attributed to in-time pile-up
      int method = 0;
      const auto tref = cand.trackRef();
      if (tref.isNonnull() && tref.isAvailable() && tref.id() == tracks.id() && tref.key() < simOfTrack.size() &&
          simOfTrack[tref.key()] >= 0) {
        shares[simOfTrack[tref.key()]] = cand.energy();
        method = 1;
      } else if (pileup_ && tref.isNonnull() && tref.isAvailable() && tref.id() == tracks.id() &&
                 tref.key() < puTrack.size() && puTrack[tref.key()]) {
        pu = cand.energy();
        method = 1;
      } else {
        // calorimeter attribution: reconstructed energy of the cluster cells
        double recTotal = 0, recPU = 0;
        std::map<int, double> recShares;
        for (const auto& eib : cand.elementsInBlocks()) {
          const reco::PFBlockRef& bref = eib.first;
          if (bref.isNull() || !bref.isAvailable() || eib.second >= bref->elements().size())
            continue;
          const auto& el = bref->elements()[eib.second];
          const auto cref = el.clusterRef();
          if (cref.isNull() || !cref.isAvailable())
            continue;
          if (el.type() == reco::PFBlockElement::PS1 || el.type() == reco::PFBlockElement::PS2)
            continue;
          for (const auto& hf : cref->hitsAndFractions()) {
            auto itE = recE.find(hf.first.rawId());
            if (itE == recE.end())
              continue;
            const double e = itE->second * hf.second;
            if (e <= 0)
              continue;
            recTotal += e;
            auto itC = cells.find(hf.first.rawId());
            if (itC == cells.end())
              continue;
            const double simAll = pileup_ ? itC->second->all() : itC->second->total;  // in-time sim energy of the cell
            if (simAll <= 0)
              continue;
            const double attributed = std::min(e, simAll);  // cap by the sim energy
            for (const auto& tk : itC->second->perTrack)
              recShares[tk.first] += attributed * tk.second / simAll;
            if (pileup_)
              recPU += attributed * itC->second->puTotal / simAll;
          }
        }
        if (recTotal > 0) {
          method = 2;
          const double scale = cand.energy() / recTotal;  // calibrated candidate energy vs raw cells
          for (const auto& kv : recShares)
            shares[kv.first] = kv.second * scale;
          pu = recPU * scale;
        }
      }
      double signal = 0;
      int dominant = -1;
      double dominantE = 0;
      for (const auto& kv : shares) {
        signal += kv.second;
        if (kv.second > dominantE) {
          dominantE = kv.second;
          dominant = kv.first;
        }
        if (kv.second >= minShareFraction_ * cand.energy()) {
          sCand.push_back(row);
          sSim.push_back(kv.first);
          sEnergy.push_back(kv.second);
          sFraction.push_back(cand.energy() > 0 ? kv.second / cand.energy() : 0.f);
          shareCand->push_back(static_cast<int>(c));
          shareSim->push_back(kv.first);
          shareE->push_back(kv.second);
        }
      }
      cRow.push_back(row);
      cSignalFrac.push_back(cand.energy() > 0 ? std::min(1.0, signal / cand.energy()) : 0.f);
      cPUFrac.push_back(cand.energy() > 0 ? std::min(1.0, pu / cand.energy()) : 0.f);
      cDominant.push_back(dominant);
      cDominantFrac.push_back(cand.energy() > 0 ? dominantE / cand.energy() : 0.f);
      cMethod.push_back(method);
      ++row;
    }

    auto cTable = std::make_unique<nanoaod::FlatTable>(cRow.size(), "PFCandTruth", false, false);
    cTable->setDoc("attribution of every PFCand row to the simulated particles of the signal event (track association for charged candidates, sim-hit shares of the cluster cells otherwise)");
    cTable->addColumn<float>("signalFraction", cSignalFrac, "fraction of the candidate energy attributed to signal particles (the rest is pile-up, noise or unmatched)", 10);
    cTable->addColumn<int32_t>("simTrackIdx", cDominant, "row in the SimTrack table of the particle with the largest share (-1: none)");
    cTable->addColumn<float>("simTrackFraction", cDominantFrac, "fraction of the candidate energy from that particle", 10);
    cTable->addColumn<int32_t>("method", cMethod, "0 none, 1 track association, 2 calorimeter cells");
    if (pileup_)
      cTable->addColumn<float>("puFraction", cPUFrac, "fraction of the candidate energy attributed to in-time pile-up particles (track of a pile-up TrackingParticle, or pile-up share of the cluster cells); 1 - signalFraction - puFraction is noise, out-of-time pile-up and calibration", 10);

    auto sTable = std::make_unique<nanoaod::FlatTable>(sCand.size(), "PFCandSim", false, false);
    sTable->setDoc("(PFCand, SimTrack) energy shares above minShareFraction");
    sTable->addColumn<int32_t>("candIdx", sCand, "row in the PFCand table");
    sTable->addColumn<int32_t>("simTrackIdx", sSim, "row in the SimTrack table");
    sTable->addColumn<float>("energy", sEnergy, "candidate energy attributed to the particle [GeV]", 10);
    sTable->addColumn<float>("fraction", sFraction, "energy / candidate energy", 10);

    event.put(std::move(cTable), "candidates");
    event.put(std::move(sTable), "shares");
    event.put(std::move(shareCand), "shareCand");
    event.put(std::move(shareSim), "shareSimTrack");
    event.put(std::move(shareE), "shareEnergy");
  }

private:
  edm::EDGetTokenT<reco::PFCandidateCollection> candsToken_;
  edm::EDGetTokenT<reco::TrackCollection> tracksToken_;
  edm::EDGetTokenT<reco::RecoToSimCollection> recoToSimToken_;
  edm::EDGetTokenT<edm::SimTrackContainer> simTracksToken_;
  edm::EDGetTokenT<EcalRecHitCollection> ebToken_, eeToken_, esToken_;
  edm::EDGetTokenT<HBHERecHitCollection> hbheToken_;
  edm::EDGetTokenT<HFRecHitCollection> hfToken_;
  edm::EDGetTokenT<HORecHitCollection> hoToken_;
  bool pileup_;
  pico::CaloSimHits simHits_;
  double candMinPt_;
  double minShareFraction_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoPFCandTruthProducer);
