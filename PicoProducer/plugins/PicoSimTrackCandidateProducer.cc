// Turn the Geant4 SimTracks of the signal event into reco::GenParticle
// candidates so that standard jet clustering (FastjetJetProducer) can build
// "sim jets": jets of the particles after the detector-level decays and
// conversions that Geant4 simulated (K0S, Lambda, pi/K decays in flight,
// photon conversions, ...), as opposed to generator-level GenJets.
//
// selection = "leaves": SimTracks that end the stored simulation tree: no
//             stored daughters, or daughters carrying less than
//             maxDaughterEnergyFraction of the track energy (delta rays,
//             bremsstrahlung: the track itself continues) (default);
//           = "boundary": the same terminal particles, but with the momentum
//             Geant4 recorded when they crossed the tracker/calo boundary
//             (after the energy loss and bending in the tracker); particles born
//             inside the calorimeter keep their production momentum;
//           = "primaries": SimTracks that come directly from the generator.
// Neutrinos are dropped by default (as in ak4GenJetsNoNu).
//
// Also writes std::vector<int> ("simTrackIndex"): the index in the SimTrack
// collection of every candidate, so that tables can link back to SimTrack rows.
#include <cmath>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

class PicoSimTrackCandidateProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoSimTrackCandidateProducer(const edm::ParameterSet& cfg)
      : tracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        verticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        selection_(cfg.getParameter<std::string>("selection")),
        excludeNeutrinos_(cfg.getParameter<bool>("excludeNeutrinos")),
        signalOnly_(cfg.getParameter<bool>("signalOnly")),
        minPt_(cfg.getParameter<double>("minPt")),
        maxDaughterEnergyFraction_(cfg.getParameter<double>("maxDaughterEnergyFraction")) {
    if (selection_ != "leaves" && selection_ != "boundary" && selection_ != "primaries")
      throw cms::Exception("Configuration") << "selection must be leaves, boundary or primaries (got " << selection_ << ")";
    produces<reco::GenParticleCollection>();
    produces<std::vector<int>>("simTrackIndex");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<std::string>("selection", "leaves");
    desc.add<bool>("excludeNeutrinos", true);
    desc.add<bool>("signalOnly", true);
    desc.add<double>("minPt", 0.0);
    desc.add<double>("maxDaughterEnergyFraction", 0.5);
    descriptions.addWithDefaultLabel(desc);
  }

  static bool isNeutrino(int pdgId) {
    const int a = std::abs(pdgId);
    return a == 12 || a == 14 || a == 16;
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& vertices = event.get(verticesToken_);

    // energy of the stored daughters of every trackId (0 for leaves of the sim tree)
    std::unordered_map<unsigned int, double> daughterEnergy;
    for (const auto& t : tracks) {
      const int v = t.vertIndex();
      if (v < 0 || size_t(v) >= vertices.size() || vertices[v].noParent())
        continue;
      daughterEnergy[static_cast<unsigned int>(vertices[v].parentIndex())] += t.momentum().E();
    }

    auto out = std::make_unique<reco::GenParticleCollection>();
    auto index = std::make_unique<std::vector<int>>();
    for (size_t i = 0; i < tracks.size(); ++i) {
      const SimTrack& t = tracks[i];
      if (signalOnly_ && (t.eventId().bunchCrossing() != 0 || t.eventId().event() != 0))
        continue;
      if (excludeNeutrinos_ && isNeutrino(t.type()))
        continue;
      math::XYZTLorentzVectorD p4 = t.momentum();
      if (selection_ == "leaves" || selection_ == "boundary") {
        auto it = daughterEnergy.find(t.trackId());
        if (it != daughterEnergy.end() && it->second >= maxDaughterEnergyFraction_ * p4.E())
          continue;
        if (selection_ == "boundary" && t.crossedBoundary() && t.getMomentumAtBoundary().E() > 0)
          p4 = math::XYZTLorentzVectorD(t.getMomentumAtBoundary());
      } else {  // primaries
        if (t.noGenpart())
          continue;
      }
      if (p4.pt() < minPt_)
        continue;
      math::XYZPoint vtx(0, 0, 0);
      if (!t.noVertex() && t.vertIndex() >= 0 && size_t(t.vertIndex()) < vertices.size()) {
        const auto& pos = vertices[t.vertIndex()].position();
        vtx = math::XYZPoint(pos.x(), pos.y(), pos.z());
      }
      out->emplace_back(static_cast<int>(std::lround(t.charge())), math::XYZTLorentzVector(p4), vtx, t.type(), 1, true);
      index->push_back(static_cast<int>(i));
    }
    event.put(std::move(out));
    event.put(std::move(index), "simTrackIndex");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> verticesToken_;
  std::string selection_;
  bool excludeNeutrinos_;
  bool signalOnly_;
  double minPt_;
  double maxDaughterEnergyFraction_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimTrackCandidateProducer);
