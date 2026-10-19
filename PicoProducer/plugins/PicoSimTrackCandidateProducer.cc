// Turn the Geant4 SimTracks of the signal event into reco::GenParticle
// candidates so that standard jet clustering (FastjetJetProducer) can build
// "sim jets": jets of the particles after the detector-level decays and
// conversions that Geant4 simulated (K0S, Lambda, pi/K decays in flight,
// photon conversions, ...), as opposed to generator-level GenJets.
//
// selection = "entrance": the calorimeter-entrance particles (PicoCaloEntrance.h):
//             the cut through the stored decay tree at the tracker/calo
//             boundary, taken from the "caloEntrance" products, with
//             momentum = "production" (the production momentum, daughters that
//             are entrance particles themselves taken out; default) or
//             "boundary" (the momentum Geant4 recorded at the crossing, after
//             the energy loss and bending in the tracker);
//           = "leaves": SimTracks that end the stored simulation tree: no
//             stored daughters, or daughters carrying less than
//             maxDaughterEnergyFraction of the track energy (delta rays,
//             bremsstrahlung: the track itself continues), production momentum;
//           = "boundary": the same terminal particles with the momentum at the
//             boundary crossing when recorded;
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
        momentum_(cfg.getParameter<std::string>("momentum")),
        excludeNeutrinos_(cfg.getParameter<bool>("excludeNeutrinos")),
        signalOnly_(cfg.getParameter<bool>("signalOnly")),
        minPt_(cfg.getParameter<double>("minPt")),
        maxDaughterEnergyFraction_(cfg.getParameter<double>("maxDaughterEnergyFraction")) {
    if (selection_ != "entrance" && selection_ != "leaves" && selection_ != "boundary" && selection_ != "primaries")
      throw cms::Exception("Configuration")
          << "selection must be entrance, leaves, boundary or primaries (got " << selection_ << ")";
    if (momentum_ != "production" && momentum_ != "boundary")
      throw cms::Exception("Configuration") << "momentum must be production or boundary (got " << momentum_ << ")";
    if (selection_ == "entrance") {
      const edm::InputTag tag = cfg.getParameter<edm::InputTag>("caloEntrance");
      entranceToken_ = consumes<std::vector<int>>(edm::InputTag(tag.label(), "isEntrance"));
      const std::vector<std::string> names = momentum_ == "production"
                                                 ? std::vector<std::string>{"prodPx", "prodPy", "prodPz", "prodE"}
                                                 : std::vector<std::string>{"px", "py", "pz", "e"};
      for (const auto& c : names)
        momentumTokens_.push_back(consumes<std::vector<float>>(edm::InputTag(tag.label(), c)));
    }
    produces<reco::GenParticleCollection>();
    produces<std::vector<int>>("simTrackIndex");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("caloEntrance", edm::InputTag("picoCaloEntrance"));
    desc.add<std::string>("selection", "entrance");
    desc.add<std::string>("momentum", "production");
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

    const std::vector<int>* isEntrance = nullptr;
    std::vector<const std::vector<float>*> mom;
    if (selection_ == "entrance") {
      isEntrance = &event.get(entranceToken_);
      for (const auto& tok : momentumTokens_)
        mom.push_back(&event.get(tok));
      if (isEntrance->size() != tracks.size())
        throw cms::Exception("LogicError") << "caloEntrance flags (" << isEntrance->size()
                                           << ") do not match the SimTrack collection (" << tracks.size() << ")";
    }

    // energy of the stored daughters of every trackId (0 for leaves of the sim tree)
    std::unordered_map<unsigned int, double> daughterEnergy;
    if (selection_ == "leaves" || selection_ == "boundary")
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
      if (selection_ == "entrance") {
        if (!(*isEntrance)[i])
          continue;
        p4 = math::XYZTLorentzVectorD((*mom[0])[i], (*mom[1])[i], (*mom[2])[i], (*mom[3])[i]);
        if (p4.E() <= 0)  // its entrance daughters carry all of its energy
          continue;
      } else if (selection_ == "leaves" || selection_ == "boundary") {
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
  edm::EDGetTokenT<std::vector<int>> entranceToken_;
  std::vector<edm::EDGetTokenT<std::vector<float>>> momentumTokens_;
  std::string selection_, momentum_;
  bool excludeNeutrinos_;
  bool signalOnly_;
  double minPt_;
  double maxDaughterEnergyFraction_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimTrackCandidateProducer);
