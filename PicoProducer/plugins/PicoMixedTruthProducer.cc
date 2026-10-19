// Pile-up truth of a classically mixed event (MixingModule with minimum-bias
// GEN-SIM input), extracted from the transient CrossingFrames that the mixing
// module builds for the digitisers and written as ordinary persistent
// collections. Runs in the DIGI step, where the CrossingFrames exist.
//
// Products:
//   SimTracks   "pileup"     the SimTracks of the in-time pile-up interactions (bunch
//                            crossing 0, event number > 0), with their EncodedEventId;
//                            vertex indices renumbered into the merged vertex collection
//   SimVertexs  "pileup"     their SimVertices (same renumbering)
//   PCaloHits   "EcalHitsEB", "EcalHitsEE", "EcalHitsES", "HcalHits"
//                            the calorimeter sim hits of the in-time pile-up interactions,
//                            hit by hit with their EncodedEventId and Geant4 track id
//   PCaloHits   "OotEcalHitsEB", ... "OotHcalHits"
//                            the out-of-time pile-up deposits summed per (cell, bunch
//                            crossing): one PCaloHit per pair with eventId = (bx, 0) and
//                            track id 0, for the bunch crossings in [minBunch, maxBunch]
//   int         "nInTime"    number of in-time pile-up interactions
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "SimDataFormats/CaloHit/interface/PCaloHit.h"
#include "SimDataFormats/CaloHit/interface/PCaloHitContainer.h"
#include "SimDataFormats/CrossingFrame/interface/CrossingFrame.h"
#include "SimDataFormats/CrossingFrame/interface/MixCollection.h"
#include "SimDataFormats/EncodedEventId/interface/EncodedEventId.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

class PicoMixedTruthProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoMixedTruthProducer(const edm::ParameterSet& cfg)
      : mixLabel_(cfg.getParameter<std::string>("mixLabel")),
        tracksToken_(consumes<CrossingFrame<SimTrack>>(edm::InputTag(mixLabel_, cfg.getParameter<std::string>("simTracksInstance")))),
        verticesToken_(consumes<CrossingFrame<SimVertex>>(edm::InputTag(mixLabel_, cfg.getParameter<std::string>("simVerticesInstance")))),
        minBunch_(cfg.getParameter<int>("minBunch")),
        maxBunch_(cfg.getParameter<int>("maxBunch")) {
    for (const std::string& name : cfg.getParameter<std::vector<std::string>>("caloHitInstances")) {
      caloNames_.push_back(name);
      caloTokens_.push_back(consumes<CrossingFrame<PCaloHit>>(edm::InputTag(mixLabel_, "g4SimHits" + name)));
      produces<edm::PCaloHitContainer>(name);
      produces<edm::PCaloHitContainer>("Oot" + name);
    }
    produces<edm::SimTrackContainer>("pileup");
    produces<edm::SimVertexContainer>("pileup");
    produces<int>("nInTime");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<std::string>("mixLabel", "mix");
    desc.add<std::string>("simTracksInstance", "g4SimHits");
    desc.add<std::string>("simVerticesInstance", "g4SimHits");
    desc.add<std::vector<std::string>>("caloHitInstances", {"EcalHitsEB", "EcalHitsEE", "EcalHitsES", "HcalHits"});
    desc.add<int>("minBunch", -12);
    desc.add<int>("maxBunch", 3);
    descriptions.addWithDefaultLabel(desc);
  }

  static bool isSignal(const EncodedEventId& id) { return id.bunchCrossing() == 0 && id.event() == 0; }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    // ---- in-time pile-up SimTracks and SimVertices, renumbered per interaction ------
    edm::Handle<CrossingFrame<SimTrack>> cfTracks;
    edm::Handle<CrossingFrame<SimVertex>> cfVertices;
    event.getByToken(tracksToken_, cfTracks);
    event.getByToken(verticesToken_, cfVertices);
    auto tracks = std::make_unique<edm::SimTrackContainer>();
    auto vertices = std::make_unique<edm::SimVertexContainer>();
    std::map<uint32_t, int> vertexOffset;  // eventId raw -> offset of its vertices
    std::map<uint32_t, int> interactions;
    {
      MixCollection<SimVertex> col(cfVertices.product());
      for (auto it = col.begin(); it != col.end(); ++it) {
        if (it.bunch() != 0 || isSignal(it->eventId()))
          continue;
        const uint32_t key = it->eventId().rawId();
        if (!vertexOffset.count(key))
          vertexOffset[key] = static_cast<int>(vertices->size());
        vertices->push_back(*it);
      }
    }
    {
      MixCollection<SimTrack> col(cfTracks.product());
      for (auto it = col.begin(); it != col.end(); ++it) {
        if (it.bunch() != 0 || isSignal(it->eventId()))
          continue;
        SimTrack t = *it;
        const uint32_t key = t.eventId().rawId();
        interactions[key] += 1;
        if (!t.noVertex()) {
          auto off = vertexOffset.find(key);
          if (off != vertexOffset.end())
            t.setVertexIndex(t.vertIndex() + off->second);
        }
        tracks->push_back(t);
      }
    }
    event.put(std::make_unique<int>(static_cast<int>(interactions.size())), "nInTime");
    event.put(std::move(tracks), "pileup");
    event.put(std::move(vertices), "pileup");

    // ---- calorimeter hits: in-time hit by hit, out-of-time summed per cell and crossing
    for (size_t k = 0; k < caloTokens_.size(); ++k) {
      edm::Handle<CrossingFrame<PCaloHit>> cf;
      event.getByToken(caloTokens_[k], cf);
      auto inTime = std::make_unique<edm::PCaloHitContainer>();
      std::map<std::pair<int, uint32_t>, std::pair<double, double>> oot;  // (bx, cell) -> (energy, em)
      MixCollection<PCaloHit> col(cf.product());
      for (auto it = col.begin(); it != col.end(); ++it) {
        const int bx = it.bunch();
        if (bx == 0) {
          if (isSignal(it->eventId()))
            continue;
          inTime->push_back(*it);
        } else if (bx >= minBunch_ && bx <= maxBunch_) {
          auto& e = oot[{bx, it->id()}];
          e.first += it->energy();
          e.second += it->energyEM();
        }
      }
      auto ootHits = std::make_unique<edm::PCaloHitContainer>();
      for (const auto& kv : oot) {
        PCaloHit h(kv.first.second, kv.second.second, kv.second.first - kv.second.second, 25.0 * kv.first.first, 0);
        h.setEventId(EncodedEventId(kv.first.first, 0));
        ootHits->push_back(h);
      }
      event.put(std::move(inTime), caloNames_[k]);
      event.put(std::move(ootHits), "Oot" + caloNames_[k]);
    }
  }

private:
  std::string mixLabel_;
  edm::EDGetTokenT<CrossingFrame<SimTrack>> tracksToken_;
  edm::EDGetTokenT<CrossingFrame<SimVertex>> verticesToken_;
  std::vector<std::string> caloNames_;
  std::vector<edm::EDGetTokenT<CrossingFrame<PCaloHit>>> caloTokens_;
  int minBunch_, maxBunch_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoMixedTruthProducer);
