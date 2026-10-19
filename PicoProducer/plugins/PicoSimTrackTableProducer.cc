// Pico tables of the Geant4 simulation truth of the signal event:
//   SimTrack  (instance "tracks")    one row per SimTrack (g4SimHits)
//   SimVertex (instance "vertices")  one row per SimVertex (g4SimHits)
// The two tables link to each other (SimTrack_vertIdx, SimTrack_parentIdx,
// SimVertex_parentIdx), to the GenPart table (SimTrack_genPartIdx) and to the
// sim jets built from the SimTracks (SimTrack_simJetIdx).
#include <cmath>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/JetReco/interface/Jet.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoGenParticleRowMap.h"

class PicoSimTrackTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoSimTrackTableProducer(const edm::ParameterSet& cfg)
      : tracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        verticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genParticles"))),
        genTableToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genPartTableSrc"))),
        jetsToken_(mayConsume<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("simJets"))),
        jetIndexToken_(mayConsume<std::vector<int>>(cfg.getParameter<edm::InputTag>("simJetConstituentIndex"))),
        useJets_(!cfg.getParameter<edm::InputTag>("simJets").label().empty()),
        trackName_(cfg.getParameter<std::string>("trackName")),
        vertexName_(cfg.getParameter<std::string>("vertexName")) {
    produces<nanoaod::FlatTable>("tracks");
    produces<nanoaod::FlatTable>("vertices");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("genParticles", edm::InputTag("genParticles"));
    desc.add<edm::InputTag>("genPartTableSrc", edm::InputTag("picoPrunedGenParticles"));
    desc.add<edm::InputTag>("simJets", edm::InputTag("picoAk4SimJets"));
    desc.add<edm::InputTag>("simJetConstituentIndex", edm::InputTag("picoSimTrackCandidates", "simTrackIndex"));
    desc.add<std::string>("trackName", "SimTrack");
    desc.add<std::string>("vertexName", "SimVertex");
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& vertices = event.get(verticesToken_);
    const auto& gens = event.get(genToken_);
    const auto& genTable = event.get(genTableToken_);
    const std::vector<int32_t> genRow = pico::genParticleRowMap(gens, genTable);

    std::unordered_map<unsigned int, int32_t> rowOfTrackId;
    rowOfTrackId.reserve(tracks.size());
    for (size_t i = 0; i < tracks.size(); ++i)
      rowOfTrackId.emplace(tracks[i].trackId(), static_cast<int32_t>(i));

    // vertex -> parent SimTrack row; SimTrack -> number of daughters
    std::vector<int32_t> vParent(vertices.size(), -1), vNDaughters(vertices.size(), 0);
    std::vector<int32_t> tNDaughters(tracks.size(), 0);
    std::vector<float> tDauEnergy(tracks.size(), 0.f);
    for (size_t v = 0; v < vertices.size(); ++v) {
      if (vertices[v].noParent())
        continue;
      auto it = rowOfTrackId.find(static_cast<unsigned int>(vertices[v].parentIndex()));
      if (it != rowOfTrackId.end())
        vParent[v] = it->second;
    }
    for (size_t i = 0; i < tracks.size(); ++i) {
      const int v = tracks[i].vertIndex();
      if (v >= 0 && size_t(v) < vertices.size()) {
        ++vNDaughters[v];
        if (vParent[v] >= 0) {
          ++tNDaughters[vParent[v]];
          tDauEnergy[vParent[v]] += tracks[i].momentum().E();
        }
      }
    }

    // sim jet membership
    std::vector<int32_t> tJet(tracks.size(), -1);
    if (useJets_) {
      edm::Handle<edm::View<reco::Jet>> jets;
      edm::Handle<std::vector<int>> jetIndex;
      event.getByToken(jetsToken_, jets);
      event.getByToken(jetIndexToken_, jetIndex);
      if (jets.isValid() && jetIndex.isValid()) {
        for (size_t j = 0; j < jets->size(); ++j) {
          for (unsigned d = 0; d < (*jets)[j].numberOfDaughters(); ++d) {
            const auto ptr = (*jets)[j].daughterPtr(d);
            if (ptr.isNonnull() && ptr.key() < jetIndex->size()) {
              const int st = (*jetIndex)[ptr.key()];
              if (st >= 0 && size_t(st) < tracks.size())
                tJet[st] = j;
            }
          }
        }
      }
    }

    const size_t nT = tracks.size();
    std::vector<int32_t> pdgId, charge, vertIdx, parentIdx, genPartIdx, genBarcode, nDaughters, simJetIdx;
    std::vector<uint32_t> trackId;
    std::vector<float> pt, eta, phi, p, energy, mass, vx, vy, vz, vt, tkPt, tkEta, tkPhi, bPt, bEta, bPhi;
    std::vector<uint8_t> isPrimary, isLeaf, crossedBoundary;
    std::vector<float> dauEnergyFrac;
    auto reserveAll = [nT](auto&... v) { (v.reserve(nT), ...); };
    reserveAll(pdgId, charge, vertIdx, parentIdx, genPartIdx, genBarcode, nDaughters, simJetIdx, trackId, pt, eta, phi,
               p, energy, mass, vx, vy, vz, vt, tkPt, tkEta, tkPhi, bPt, bEta, bPhi, isPrimary, isLeaf, crossedBoundary);

    for (size_t i = 0; i < nT; ++i) {
      const SimTrack& t = tracks[i];
      const auto& mom = t.momentum();
      pdgId.push_back(t.type());
      charge.push_back(static_cast<int32_t>(std::lround(t.charge())));
      pt.push_back(mom.pt());
      eta.push_back(mom.eta());
      phi.push_back(mom.phi());
      p.push_back(mom.P());
      energy.push_back(mom.E());
      mass.push_back(mom.M());
      trackId.push_back(t.trackId());
      const int v = t.vertIndex();
      const bool hasVertex = v >= 0 && size_t(v) < vertices.size();
      vertIdx.push_back(hasVertex ? v : -1);
      parentIdx.push_back(hasVertex ? vParent[v] : -1);
      if (hasVertex) {
        const auto& pos = vertices[v].position();
        vx.push_back(pos.x());
        vy.push_back(pos.y());
        vz.push_back(pos.z());
        vt.push_back(pos.t());
      } else {
        vx.push_back(0.f);
        vy.push_back(0.f);
        vz.push_back(0.f);
        vt.push_back(0.f);
      }
      // genpartIndex() is the HepMC barcode of the generator particle; the
      // genParticles collection is filled in barcode order, so barcode-1 is
      // its index. Verify the match before trusting it.
      int32_t gIdx = -1, barcode = -1;
      if (!t.noGenpart()) {
        barcode = t.genpartIndex();
        const int k = barcode - 1;
        if (k >= 0 && size_t(k) < gens.size() && gens[k].pdgId() == t.type() &&
            std::abs(gens[k].pt() - mom.pt()) < 1e-3 * std::max(1.0, mom.pt()))
          gIdx = genRow[k];
      }
      genPartIdx.push_back(gIdx);
      genBarcode.push_back(barcode);
      isPrimary.push_back(t.noGenpart() ? 0 : 1);
      nDaughters.push_back(tNDaughters[i]);
      isLeaf.push_back(tNDaughters[i] == 0 ? 1 : 0);
      dauEnergyFrac.push_back(mom.E() > 0 ? tDauEnergy[i] / mom.E() : 0.f);
      crossedBoundary.push_back(t.crossedBoundary() ? 1 : 0);
      simJetIdx.push_back(tJet[i]);
      const auto& tk = t.trackerSurfaceMomentum();
      tkPt.push_back(tk.pt());
      tkEta.push_back(tk.pt() > 0 ? tk.eta() : 0.f);
      tkPhi.push_back(tk.pt() > 0 ? tk.phi() : 0.f);
      const auto& bm = t.getMomentumAtBoundary();
      bPt.push_back(t.crossedBoundary() ? bm.pt() : -1.f);
      bEta.push_back(t.crossedBoundary() && bm.pt() > 0 ? bm.eta() : 0.f);
      bPhi.push_back(t.crossedBoundary() && bm.pt() > 0 ? bm.phi() : 0.f);
    }

    auto tTable = std::make_unique<nanoaod::FlatTable>(nT, trackName_, false, false);
    tTable->setDoc("Geant4 SimTracks of the signal event (g4SimHits): generator primaries plus the decay and conversion products simulated in the detector");
    tTable->addColumn<int32_t>("pdgId", pdgId, "PDG identifier");
    tTable->addColumn<int32_t>("charge", charge, "electric charge");
    tTable->addColumn<float>("pt", pt, "pt at production", 10);
    tTable->addColumn<float>("eta", eta, "eta at production", 10);
    tTable->addColumn<float>("phi", phi, "phi at production", 10);
    tTable->addColumn<float>("p", p, "momentum at production", 10);
    tTable->addColumn<float>("energy", energy, "energy at production", 10);
    tTable->addColumn<float>("mass", mass, "mass", 10);
    tTable->addColumn<float>("vx", vx, "production vertex x [cm]", 10);
    tTable->addColumn<float>("vy", vy, "production vertex y [cm]", 10);
    tTable->addColumn<float>("vz", vz, "production vertex z [cm]", 10);
    tTable->addColumn<float>("vt", vt, "production vertex time [ns]", 10);
    tTable->addColumn<int32_t>("vertIdx", vertIdx, "row of the production vertex in the " + vertexName_ + " table (-1: none)");
    tTable->addColumn<int32_t>("parentIdx", parentIdx, "row of the parent SimTrack (-1: generator primary or unknown)");
    tTable->addColumn<int32_t>("genPartIdx", genPartIdx, "row in the GenPart table of the generator particle (-1: not a primary or pruned away)");
    tTable->addColumn<int32_t>("genBarcode", genBarcode, "HepMC barcode of the generator particle (-1: not a primary)");
    tTable->addColumn<uint8_t>("isPrimary", isPrimary, "1 if the track comes directly from the generator");
    tTable->addColumn<int32_t>("nDaughters", nDaughters, "number of SimTracks produced at the decay/interaction vertex of this track");
    tTable->addColumn<uint8_t>("isLeaf", isLeaf, "1 if no daughter SimTrack is stored (end point of the stored sim tree)");
    tTable->addColumn<float>("dauEnergyFrac", dauEnergyFrac, "energy of the stored daughters / energy of this track (~1: decay or conversion, ~0: delta ray or brem, the track continues)", 10);
    tTable->addColumn<uint8_t>("crossedBoundary", crossedBoundary, "1 if Geant4 recorded the tracker/calo boundary crossing");
    tTable->addColumn<float>("boundaryPt", bPt, "pt at the tracker/calo boundary (-1 if not recorded)", 10);
    tTable->addColumn<float>("boundaryEta", bEta, "eta at the tracker/calo boundary", 10);
    tTable->addColumn<float>("boundaryPhi", bPhi, "phi at the tracker/calo boundary", 10);
    tTable->addColumn<float>("tkPt", tkPt, "pt at the tracker surface (0 if not recorded)", 10);
    tTable->addColumn<float>("tkEta", tkEta, "eta at the tracker surface", 10);
    tTable->addColumn<float>("tkPhi", tkPhi, "phi at the tracker surface", 10);
    tTable->addColumn<int32_t>("simJetIdx", simJetIdx, "row in the SimJet table of the jet this track is clustered into (-1: none)");
    tTable->addColumn<uint32_t>("trackId", trackId, "Geant4 track id");

    const size_t nV = vertices.size();
    std::vector<float> x, y, z, tm;
    std::vector<uint32_t> processType, vertexId;
    for (size_t v = 0; v < nV; ++v) {
      const auto& pos = vertices[v].position();
      x.push_back(pos.x());
      y.push_back(pos.y());
      z.push_back(pos.z());
      tm.push_back(pos.t());
      processType.push_back(vertices[v].processType());
      vertexId.push_back(vertices[v].vertexId());
    }
    auto vTable = std::make_unique<nanoaod::FlatTable>(nV, vertexName_, false, false);
    vTable->setDoc("Geant4 SimVertices of the signal event (g4SimHits)");
    vTable->addColumn<float>("x", x, "x [cm]", 10);
    vTable->addColumn<float>("y", y, "y [cm]", 10);
    vTable->addColumn<float>("z", z, "z [cm]", 10);
    vTable->addColumn<float>("t", tm, "time [ns]", 10);
    vTable->addColumn<int32_t>("parentIdx", vParent, "row of the SimTrack that produced this vertex (-1: primary vertex)");
    vTable->addColumn<int32_t>("nDaughters", vNDaughters, "number of SimTracks starting at this vertex");
    vTable->addColumn<uint32_t>("processType", processType, "Geant4 process type that created the vertex");
    vTable->addColumn<uint32_t>("vertexId", vertexId, "Geant4 vertex id");

    event.put(std::move(tTable), "tracks");
    event.put(std::move(vTable), "vertices");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> verticesToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genTableToken_;
  edm::EDGetTokenT<edm::View<reco::Jet>> jetsToken_;
  edm::EDGetTokenT<std::vector<int>> jetIndexToken_;
  bool useJets_;
  std::string trackName_;
  std::string vertexName_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimTrackTableProducer);
