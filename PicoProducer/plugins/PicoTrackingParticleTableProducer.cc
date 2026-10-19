// Pico tables of the TrackingParticles (charged simulated particles with hits
// in the tracker, signal and pile-up) and of their association to reco tracks:
//   TP          (instance "particles")  one row per selected TrackingParticle
//   TrackTPLink (instance "links")      one row per (Track, TP) association
//
// The association maps (reco::RecoToSimCollection / SimToRecoCollection) may
// have been produced on a different TrackingParticle collection (e.g. the
// prunedTrackingParticles of the premixed samples); their entries are matched
// to the rows of the TP table through (EncodedEventId, Geant4 track id).
#include <cmath>
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

#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "SimDataFormats/Associations/interface/TrackToTrackingParticleAssociator.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/TrackingAnalysis/interface/TrackingParticle.h"
#include "SimDataFormats/TrackingAnalysis/interface/TrackingParticleFwd.h"
#include "SimDataFormats/TrackingAnalysis/interface/TrackingVertex.h"

#include "PicoGenParticleRowMap.h"

class PicoTrackingParticleTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoTrackingParticleTableProducer(const edm::ParameterSet& cfg)
      : tpToken_(consumes<TrackingParticleCollection>(cfg.getParameter<edm::InputTag>("src"))),
        tracksToken_(consumes<reco::TrackCollection>(cfg.getParameter<edm::InputTag>("tracks"))),
        recoToSimToken_(mayConsume<reco::RecoToSimCollection>(cfg.getParameter<edm::InputTag>("association"))),
        simToRecoToken_(mayConsume<reco::SimToRecoCollection>(cfg.getParameter<edm::InputTag>("association"))),
        useAssociation_(!cfg.getParameter<edm::InputTag>("association").label().empty()),
        genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genParticles"))),
        genTableToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genPartTableSrc"))),
        simTracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        name_(cfg.getParameter<std::string>("name")),
        linkName_(cfg.getParameter<std::string>("linkName")),
        qualityDoc_(cfg.getParameter<std::string>("qualityDoc")),
        signalMinPt_(cfg.getParameter<double>("signalMinPt")),
        pileupMinPt_(cfg.getParameter<double>("pileupMinPt")),
        trackTableMinPt_(cfg.getParameter<double>("trackTableMinPt")) {
    produces<nanoaod::FlatTable>("particles");
    produces<nanoaod::FlatTable>("links");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("src", edm::InputTag("mix", "MergedTrackTruth"));
    desc.add<edm::InputTag>("tracks", edm::InputTag("generalTracks"));
    desc.add<edm::InputTag>("association", edm::InputTag("picoTrackingParticleRecoTrackAssociation"));
    desc.add<edm::InputTag>("genParticles", edm::InputTag("genParticles"));
    desc.add<edm::InputTag>("genPartTableSrc", edm::InputTag("picoPrunedGenParticles"));
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<std::string>("name", "TP");
    desc.add<std::string>("linkName", "TrackTPLink");
    desc.add<std::string>("qualityDoc", "association quality");
    desc.add<double>("signalMinPt", 0.0);
    desc.add<double>("pileupMinPt", 1.0);
    desc.add<double>("trackTableMinPt", 0.0);
    descriptions.addWithDefaultLabel(desc);
  }

  using TPKey = std::pair<uint32_t, uint32_t>;  // (EncodedEventId raw, g4 track id)

  static TPKey keyOf(const TrackingParticle& tp) {
    const auto& g4 = tp.g4Tracks();
    return TPKey(tp.eventId().rawId(), g4.empty() ? 0u : g4.front().trackId());
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<TrackingParticleCollection> tpsHandle;
    event.getByToken(tpToken_, tpsHandle);
    const auto& tps = *tpsHandle;
    edm::Handle<reco::TrackCollection> tracks;
    event.getByToken(tracksToken_, tracks);
    const auto& gens = event.get(genToken_);
    const auto& genTable = event.get(genTableToken_);
    const auto& simTracks = event.get(simTracksToken_);
    const std::vector<int32_t> genRow = pico::genParticleRowMap(gens, genTable);

    std::unordered_map<uint32_t, int32_t> simTrackRow;
    simTrackRow.reserve(simTracks.size());
    for (size_t i = 0; i < simTracks.size(); ++i)
      simTrackRow.emplace(simTracks[i].trackId(), static_cast<int32_t>(i));

    std::vector<int32_t> trackRow(tracks->size(), -1);
    for (size_t i = 0, row = 0; i < tracks->size(); ++i)
      if ((*tracks)[i].pt() >= trackTableMinPt_)
        trackRow[i] = row++;

    // selection and row map of the TP table
    std::vector<int32_t> tpRow(tps.size(), -1);
    std::map<TPKey, int32_t> rowOfKey;
    int32_t nRows = 0;
    for (size_t i = 0; i < tps.size(); ++i) {
      const auto& tp = tps[i];
      const bool signal = tp.eventId().bunchCrossing() == 0 && tp.eventId().event() == 0;
      if (tp.pt() < (signal ? signalMinPt_ : pileupMinPt_))
        continue;
      tpRow[i] = nRows++;
      rowOfKey.emplace(keyOf(tp), tpRow[i]);
    }

    std::vector<float> pt, eta, phi, mass, vx, vy, vz, decayX, decayY, decayZ;
    std::vector<int32_t> charge, pdgId, status, bx, evt, nHits, nLayers, nG4, genPartIdx, simTrackIdx, parentIdx,
        nDecayVertices;
    std::vector<uint8_t> isSignal;
    auto reserveAll = [nRows](auto&... v) { (v.reserve(nRows), ...); };
    reserveAll(pt, eta, phi, mass, vx, vy, vz, decayX, decayY, decayZ, charge, pdgId, status, bx, evt, nHits, nLayers,
               nG4, genPartIdx, simTrackIdx, parentIdx, nDecayVertices, isSignal);

    for (size_t i = 0; i < tps.size(); ++i) {
      if (tpRow[i] < 0)
        continue;
      const auto& tp = tps[i];
      const bool signal = tp.eventId().bunchCrossing() == 0 && tp.eventId().event() == 0;
      pt.push_back(tp.pt());
      eta.push_back(tp.eta());
      phi.push_back(tp.phi());
      mass.push_back(tp.mass());
      charge.push_back(static_cast<int32_t>(std::lround(tp.charge())));
      pdgId.push_back(tp.pdgId());
      status.push_back(tp.status());
      vx.push_back(tp.vx());
      vy.push_back(tp.vy());
      vz.push_back(tp.vz());
      bx.push_back(tp.eventId().bunchCrossing());
      evt.push_back(tp.eventId().event());
      isSignal.push_back(signal ? 1 : 0);
      nHits.push_back(tp.numberOfTrackerHits());
      nLayers.push_back(tp.numberOfTrackerLayers());
      nG4.push_back(static_cast<int32_t>(tp.g4Tracks().size()));

      int32_t gIdx = -1;
      for (const auto& gref : tp.genParticles()) {
        if (gref.isNonnull() && gref.isAvailable() && gref.key() < genRow.size()) {
          gIdx = genRow[gref.key()];
          break;
        }
      }
      genPartIdx.push_back(gIdx);

      int32_t sIdx = -1;
      if (signal && !tp.g4Tracks().empty()) {
        auto it = simTrackRow.find(tp.g4Tracks().front().trackId());
        if (it != simTrackRow.end())
          sIdx = it->second;
      }
      simTrackIdx.push_back(sIdx);

      int32_t pIdx = -1;
      const auto& pv = tp.parentVertex();
      if (pv.isNonnull() && pv.isAvailable()) {
        for (auto src = pv->sourceTracks_begin(); src != pv->sourceTracks_end(); ++src) {
          if (src->isNonnull() && src->id() == tpsHandle.id() && src->key() < tpRow.size()) {
            pIdx = tpRow[src->key()];
            break;
          }
        }
      }
      parentIdx.push_back(pIdx);

      const auto& dvs = tp.decayVertices();
      nDecayVertices.push_back(static_cast<int32_t>(dvs.size()));
      if (!dvs.empty() && dvs[0].isNonnull() && dvs[0].isAvailable()) {
        const auto& pos = dvs[0]->position();
        decayX.push_back(pos.x());
        decayY.push_back(pos.y());
        decayZ.push_back(pos.z());
      } else {
        decayX.push_back(-999.f);
        decayY.push_back(-999.f);
        decayZ.push_back(-999.f);
      }
    }

    // ---- track <-> TP links ----------------------------------------------
    struct Quality {
      float recoToSim = 0.f;
      float simToReco = 0.f;
      bool hasRecoToSim = false;
      bool hasSimToReco = false;
    };
    std::map<std::pair<int32_t, int32_t>, Quality> links;  // (track row, tp row)
    std::vector<int32_t> lTrackKey;
    if (useAssociation_) {
      edm::Handle<reco::RecoToSimCollection> recoToSim;
      edm::Handle<reco::SimToRecoCollection> simToReco;
      event.getByToken(recoToSimToken_, recoToSim);
      event.getByToken(simToRecoToken_, simToReco);
      auto trackRowOf = [&](const edm::RefToBase<reco::Track>& tr) -> int32_t {
        if (tr.isNull() || tr.id() != tracks.id() || tr.key() >= trackRow.size())
          return -2;
        return trackRow[tr.key()];
      };
      auto tpRowOf = [&](const TrackingParticleRef& ref) -> int32_t {
        if (ref.isNull() || !ref.isAvailable())
          return -2;
        if (ref.id() == tpsHandle.id())
          return ref.key() < tpRow.size() ? tpRow[ref.key()] : -2;
        auto it = rowOfKey.find(keyOf(*ref));
        return it == rowOfKey.end() ? -2 : it->second;
      };
      if (recoToSim.isValid()) {
        for (const auto& entry : *recoToSim) {
          const int32_t tr = trackRowOf(entry.key);
          if (tr < 0)
            continue;
          for (const auto& tpq : entry.val) {
            const int32_t tp = tpRowOf(tpq.first);
            if (tp < 0)
              continue;
            auto& q = links[{tr, tp}];
            q.recoToSim = tpq.second;
            q.hasRecoToSim = true;
          }
        }
      }
      if (simToReco.isValid()) {
        for (const auto& entry : *simToReco) {
          const int32_t tp = tpRowOf(entry.key);
          if (tp < 0)
            continue;
          for (const auto& trq : entry.val) {
            const int32_t tr = trackRowOf(trq.first);
            if (tr < 0)
              continue;
            auto& q = links[{tr, tp}];
            q.simToReco = trq.second;
            q.hasSimToReco = true;
          }
        }
      }
    }
    std::vector<int32_t> lTrack, lTP;
    std::vector<float> lR2S, lS2R;
    std::vector<uint8_t> lHasR2S, lHasS2R;
    for (const auto& kv : links) {
      lTrack.push_back(kv.first.first);
      lTP.push_back(kv.first.second);
      lR2S.push_back(kv.second.recoToSim);
      lS2R.push_back(kv.second.simToReco);
      lHasR2S.push_back(kv.second.hasRecoToSim ? 1 : 0);
      lHasS2R.push_back(kv.second.hasSimToReco ? 1 : 0);
    }

    auto table = std::make_unique<nanoaod::FlatTable>(nRows, name_, false, false);
    table->setDoc("TrackingParticles (" + std::string("charged simulated particles, signal and pile-up; pile-up above pileupMinPt") + ")");
    table->addColumn<float>("pt", pt, "pt", 10);
    table->addColumn<float>("eta", eta, "eta", 10);
    table->addColumn<float>("phi", phi, "phi", 10);
    table->addColumn<float>("mass", mass, "mass", 10);
    table->addColumn<int32_t>("charge", charge, "electric charge");
    table->addColumn<int32_t>("pdgId", pdgId, "PDG identifier");
    table->addColumn<int32_t>("status", status, "generator status of the matched GenParticle (-99 if none)");
    table->addColumn<float>("vx", vx, "production vertex x [cm]", 10);
    table->addColumn<float>("vy", vy, "production vertex y [cm]", 10);
    table->addColumn<float>("vz", vz, "production vertex z [cm]", 10);
    table->addColumn<int32_t>("bx", bx, "bunch crossing of the originating event (0: in time)");
    table->addColumn<int32_t>("event", evt, "index of the originating event within the bunch crossing (0: signal)");
    table->addColumn<uint8_t>("isSignal", isSignal, "1 for the hard-scatter event (bx == 0 and event == 0)");
    table->addColumn<int32_t>("nTrackerHits", nHits, "number of simulated tracker hits");
    table->addColumn<int32_t>("nTrackerLayers", nLayers, "number of tracker layers with simulated hits");
    table->addColumn<int32_t>("nG4Tracks", nG4, "number of Geant4 tracks merged into this particle");
    table->addColumn<int32_t>("genPartIdx", genPartIdx, "row in the GenPart table (-1: no generator particle or pruned away)");
    table->addColumn<int32_t>("simTrackIdx", simTrackIdx, "row in the SimTrack table of the first Geant4 track (-1: pile-up or not found)");
    table->addColumn<int32_t>("parentIdx", parentIdx, "row of the parent TrackingParticle (-1: none or not in the table)");
    table->addColumn<int32_t>("nDecayVertices", nDecayVertices, "number of decay vertices");
    table->addColumn<float>("decayX", decayX, "x of the first decay vertex [cm] (-999: none)", 10);
    table->addColumn<float>("decayY", decayY, "y of the first decay vertex [cm] (-999: none)", 10);
    table->addColumn<float>("decayZ", decayZ, "z of the first decay vertex [cm] (-999: none)", 10);

    auto linkTable = std::make_unique<nanoaod::FlatTable>(lTrack.size(), linkName_, false, false);
    linkTable->setDoc("reco track <-> TrackingParticle associations; quality: " + qualityDoc_);
    linkTable->addColumn<int32_t>("trackIdx", lTrack, "row in the Track table");
    linkTable->addColumn<int32_t>("tpIdx", lTP, "row in the " + name_ + " table");
    linkTable->addColumn<float>("recoToSimQuality", lR2S, "reco->sim quality, " + qualityDoc_ + " (valid when hasRecoToSim)", 10);
    linkTable->addColumn<float>("simToRecoQuality", lS2R, "sim->reco quality, " + qualityDoc_ + " (valid when hasSimToReco)", 10);

    linkTable->addColumn<uint8_t>("hasRecoToSim", lHasR2S, "1 if the pair is in the reco->sim map");
    linkTable->addColumn<uint8_t>("hasSimToReco", lHasS2R, "1 if the pair is in the sim->reco map");

    event.put(std::move(table), "particles");
    event.put(std::move(linkTable), "links");
  }

private:
  edm::EDGetTokenT<TrackingParticleCollection> tpToken_;
  edm::EDGetTokenT<reco::TrackCollection> tracksToken_;
  edm::EDGetTokenT<reco::RecoToSimCollection> recoToSimToken_;
  edm::EDGetTokenT<reco::SimToRecoCollection> simToRecoToken_;
  bool useAssociation_;
  edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genTableToken_;
  edm::EDGetTokenT<edm::SimTrackContainer> simTracksToken_;
  std::string name_;
  std::string linkName_;
  std::string qualityDoc_;
  double signalMinPt_;
  double pileupMinPt_;
  double trackTableMinPt_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoTrackingParticleTableProducer);
