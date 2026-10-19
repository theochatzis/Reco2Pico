// Flags the calorimeter-entrance particles among the Geant4 SimTracks of the
// signal event (see PicoCaloEntrance.h for the definition) from the SimTrack
// tree and the calorimeter sim hits.
//
// Products, all parallel to the SimTrack collection:
//   isEntrance    std::vector<int>  1 for an entrance particle
//   entranceOf    std::vector<int>  row of the entrance particle every track belongs to
//                                   (itself or an ancestor), -1 if none
//   ownsHits      std::vector<int>  1 if calorimeter sim hits reference the track
//   reachesCalo   std::vector<int>  1 if the track or a chain of daughters born outside
//                                   the tracker volume reached the calorimeter
//   prodPx, prodPy, prodPz, prodE   std::vector<float>  the production momentum as an entrance
//                                   particle (daughters taken out, see PicoCaloEntrance.h)
//   px, py, pz, e                   std::vector<float>  the momentum at the calorimeter face
#include <cstdint>
#include <memory>
#include <unordered_set>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoCaloEntrance.h"
#include "PicoCaloSimHits.h"

class PicoCaloEntranceProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoCaloEntranceProducer(const edm::ParameterSet& cfg)
      : tracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        verticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        simHits_(cfg, consumesCollector()),
        trackerMaxRadius_(cfg.getParameter<double>("trackerMaxRadius")),
        trackerMaxAbsZ_(cfg.getParameter<double>("trackerMaxAbsZ")),
        pileup_(cfg.getParameter<bool>("pileup")) {
    produces<std::vector<int>>("isEntrance");
    produces<std::vector<int>>("entranceOf");
    produces<std::vector<int>>("ownsHits");
    produces<std::vector<int>>("reachesCalo");
    for (const char* c : {"prodPx", "prodPy", "prodPz", "prodE", "px", "py", "pz", "e"})
      produces<std::vector<float>>(c);
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    pico::CaloSimHits::fillDescription(desc);
    desc.add<double>("trackerMaxRadius", 123.0);
    desc.add<double>("trackerMaxAbsZ", 293.0);
    desc.add<bool>("pileup", false);  // simTracks/simVertices are the in-time pile-up ones: use the pile-up hits
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& vertices = event.get(verticesToken_);
    std::unordered_set<uint64_t> hitKeys;
    simHits_.hitTrackKeys(event, setup, hitKeys, pileup_);
    const pico::CaloEntrance ce = pico::caloEntrance(tracks, vertices, hitKeys, trackerMaxRadius_, trackerMaxAbsZ_);

    auto toInt = [](const std::vector<uint8_t>& v) {
      return std::make_unique<std::vector<int>>(v.begin(), v.end());
    };
    event.put(toInt(ce.isEntrance), "isEntrance");
    event.put(std::make_unique<std::vector<int>>(ce.entranceOf), "entranceOf");
    event.put(toInt(ce.ownsHits), "ownsHits");
    event.put(toInt(ce.reachesCalo), "reachesCalo");
    auto putMomenta = [&](const std::vector<math::XYZTLorentzVectorD>& v, const char* nx, const char* ny, const char* nz, const char* ne) {
      auto px = std::make_unique<std::vector<float>>(), py = std::make_unique<std::vector<float>>(),
           pz = std::make_unique<std::vector<float>>(), e = std::make_unique<std::vector<float>>();
      for (const auto& p4 : v) {
        px->push_back(p4.px());
        py->push_back(p4.py());
        pz->push_back(p4.pz());
        e->push_back(p4.e());
      }
      event.put(std::move(px), nx);
      event.put(std::move(py), ny);
      event.put(std::move(pz), nz);
      event.put(std::move(e), ne);
    };
    putMomenta(ce.production, "prodPx", "prodPy", "prodPz", "prodE");
    putMomenta(ce.boundary, "px", "py", "pz", "e");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> verticesToken_;
  pico::CaloSimHits simHits_;
  double trackerMaxRadius_, trackerMaxAbsZ_;
  bool pileup_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoCaloEntranceProducer);
