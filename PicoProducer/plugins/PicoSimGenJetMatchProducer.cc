// Ancestry-based matching of sim jets (anti-kt of Geant4 SimTracks) to gen jets
// (anti-kt of generator particles), in the spirit of the HGCAL trackster <->
// sim-trackster scores: no geometry, only shared energy.
//
// Every SimTrack descends from exactly one generator primary through the
// stored Geant4 decay tree (SimVertex parent links), and every generator
// particle is a constituent of at most one gen jet. For a (sim jet s, gen jet g)
// pair:
//   sharedEnergy = sum of the energies (as clustered) of the constituents of s
//                  whose generator ancestor is a constituent of g
//   simFraction  = sharedEnergy / E(s)          "how much of the sim jet comes from g"
//   genFraction  = sum over constituents p of g of E(p) * f_s(p) / E(g)
//                  with f_s(p) the fraction of the clustered descendant energy of p
//                  that ended up in s                   "how much of the gen jet is found in s"
// Tables:
//   SimGenJetMatch (instance "matches")          one row per pair with sharedEnergy > 0
//   GenJetConst    (instance "genConstituents")  one row per gen-jet constituent (GenPart row)
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
#include "DataFormats/JetReco/interface/Jet.h"
#include "DataFormats/Math/interface/deltaR.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoGenParticleRowMap.h"

class PicoSimGenJetMatchProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoSimGenJetMatchProducer(const edm::ParameterSet& cfg)
      : simJetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("simJets"))),
        simCandsToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("simCandidates"))),
        simIndexToken_(consumes<std::vector<int>>(cfg.getParameter<edm::InputTag>("simCandidateIndex"))),
        simTracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        simVerticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        genJetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("genJets"))),
        genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genParticles"))),
        genTableToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genPartTableSrc"))),
        matchName_(cfg.getParameter<std::string>("matchName")),
        constName_(cfg.getParameter<std::string>("genConstituentsName")),
        writeConst_(cfg.getParameter<bool>("writeGenConstituents")) {
    produces<nanoaod::FlatTable>("matches");
    if (writeConst_)
      produces<nanoaod::FlatTable>("genConstituents");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simJets", edm::InputTag("picoAk4SimJets"));
    desc.add<edm::InputTag>("simCandidates", edm::InputTag("picoSimTrackCandidates"));
    desc.add<edm::InputTag>("simCandidateIndex", edm::InputTag("picoSimTrackCandidates", "simTrackIndex"));
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("genJets", edm::InputTag("picoAk4GenJetsNoNu"));
    desc.add<edm::InputTag>("genParticles", edm::InputTag("genParticles"));
    desc.add<edm::InputTag>("genPartTableSrc", edm::InputTag("picoPrunedGenParticles"));
    desc.add<std::string>("matchName", "SimGenJetMatch");
    desc.add<std::string>("genConstituentsName", "GenJetConst");
    desc.add<bool>("writeGenConstituents", true);
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& simJets = event.get(simJetsToken_);
    const auto& simCands = event.get(simCandsToken_);
    const auto& simIndex = event.get(simIndexToken_);
    const auto& tracks = event.get(simTracksToken_);
    const auto& vertices = event.get(simVerticesToken_);
    const auto& genJets = event.get(genJetsToken_);
    edm::Handle<reco::GenParticleCollection> gensHandle;
    event.getByToken(genToken_, gensHandle);
    const auto& gens = *gensHandle;
    const auto& genTable = event.get(genTableToken_);
    const std::vector<int32_t> genRow = pico::genParticleRowMap(gens, genTable);

    // ---- generator ancestor of every SimTrack ----------------------------
    std::unordered_map<unsigned int, int> rowOfTrackId;
    for (size_t i = 0; i < tracks.size(); ++i)
      rowOfTrackId.emplace(tracks[i].trackId(), static_cast<int>(i));
    auto parentOf = [&](int i) -> int {
      const int v = tracks[i].vertIndex();
      if (v < 0 || size_t(v) >= vertices.size() || vertices[v].noParent())
        return -1;
      auto it = rowOfTrackId.find(static_cast<unsigned int>(vertices[v].parentIndex()));
      return it == rowOfTrackId.end() ? -1 : it->second;
    };
    std::vector<int> ancestorGen(tracks.size(), -2);  // index into genParticles, -1 none
    for (size_t i = 0; i < tracks.size(); ++i) {
      int cur = static_cast<int>(i);
      int guard = 0;
      while (cur >= 0 && tracks[cur].noGenpart() && guard++ < 10000)
        cur = parentOf(cur);
      int g = -1;
      if (cur >= 0 && !tracks[cur].noGenpart()) {
        const int k = tracks[cur].genpartIndex() - 1;
        if (k >= 0 && size_t(k) < gens.size() && gens[k].pdgId() == tracks[cur].type())
          g = k;
      }
      ancestorGen[i] = g;
    }

    // ---- gen jet of every generator particle ---------------------------------
    std::vector<int> genJetOf(gens.size(), -1);
    std::vector<int32_t> cJet, cGenPart;
    std::vector<float> cEnergy;
    for (size_t j = 0; j < genJets.size(); ++j) {
      const reco::Jet& jet = genJets[j];
      for (unsigned d = 0; d < jet.numberOfDaughters(); ++d) {
        const auto ptr = jet.daughterPtr(d);
        int k = -1;
        if (ptr.isNonnull() && ptr.id() == gensHandle.id())
          k = ptr.key();
        else if (ptr.isNonnull() && ptr.isAvailable()) {
          // constituent stored through an intermediate collection: match the object
          const reco::GenParticle* gp = dynamic_cast<const reco::GenParticle*>(ptr.get());
          if (gp) {
            auto key = pico::genKey(*gp);
            for (size_t m = 0; m < gens.size(); ++m)
              if (pico::genKey(gens[m]) == key) {
                k = m;
                break;
              }
          }
        }
        if (k < 0)
          continue;
        genJetOf[k] = j;
        cJet.push_back(j);
        cGenPart.push_back(genRow[k]);
        cEnergy.push_back(gens[k].energy());
      }
    }

    // ---- descendant energy bookkeeping -----------------------------------------
    // clustered energy of the descendants of gen particle k: total and per sim jet
    std::unordered_map<int, double> descTotal;
    std::map<std::pair<int, int>, double> descInSim;  // (gen k, sim jet s)
    std::vector<int> simJetOfCand(simCands.size(), -1);
    for (size_t s = 0; s < simJets.size(); ++s) {
      const reco::Jet& jet = simJets[s];
      for (unsigned d = 0; d < jet.numberOfDaughters(); ++d) {
        const auto ptr = jet.daughterPtr(d);
        if (ptr.isNonnull() && ptr.key() < simJetOfCand.size())
          simJetOfCand[ptr.key()] = s;
      }
    }
    for (size_t c = 0; c < simCands.size(); ++c) {
      const int t = c < simIndex.size() ? simIndex[c] : -1;
      if (t < 0 || size_t(t) >= tracks.size())
        continue;
      const int k = ancestorGen[t];
      if (k < 0)
        continue;
      descTotal[k] += simCands[c].energy();
      if (simJetOfCand[c] >= 0)
        descInSim[{k, simJetOfCand[c]}] += simCands[c].energy();
    }

    // ---- pair scores ------------------------------------------------------------
    struct Pair {
      double shared = 0;
      double genShared = 0;
      int n = 0;
    };
    std::map<std::pair<int, int>, Pair> pairs;  // (s, g)
    for (size_t c = 0; c < simCands.size(); ++c) {
      const int s = simJetOfCand[c];
      const int t = c < simIndex.size() ? simIndex[c] : -1;
      if (s < 0 || t < 0 || size_t(t) >= tracks.size())
        continue;
      const int k = ancestorGen[t];
      if (k < 0 || genJetOf[k] < 0)
        continue;
      auto& p = pairs[{s, genJetOf[k]}];
      p.shared += simCands[c].energy();
      p.n += 1;
    }
    for (const auto& kv : descInSim) {
      const int k = kv.first.first, s = kv.first.second;
      const int g = genJetOf[k];
      if (g < 0)
        continue;
      const double tot = descTotal[k];
      if (tot > 0)
        pairs[{s, g}].genShared += gens[k].energy() * kv.second / tot;
    }

    std::vector<int32_t> mSim, mGen, mN;
    std::vector<float> mShared, mSimFrac, mGenFrac, mDR, mPtRatio;
    std::vector<uint8_t> mBestForSim, mBestForGen;
    std::map<int, std::pair<double, size_t>> bestOfSim, bestOfGen;
    for (const auto& kv : pairs) {
      const int s = kv.first.first, g = kv.first.second;
      const double es = simJets[s].energy(), eg = genJets[g].energy();
      mSim.push_back(s);
      mGen.push_back(g);
      mN.push_back(kv.second.n);
      mShared.push_back(kv.second.shared);
      mSimFrac.push_back(es > 0 ? kv.second.shared / es : 0.f);
      mGenFrac.push_back(eg > 0 ? kv.second.genShared / eg : 0.f);
      mDR.push_back(reco::deltaR(simJets[s], genJets[g]));
      mPtRatio.push_back(genJets[g].pt() > 0 ? simJets[s].pt() / genJets[g].pt() : 0.f);
      const size_t row = mSim.size() - 1;
      if (!bestOfSim.count(s) || kv.second.shared > bestOfSim[s].first)
        bestOfSim[s] = {kv.second.shared, row};
      if (!bestOfGen.count(g) || kv.second.genShared > bestOfGen[g].first)
        bestOfGen[g] = {kv.second.genShared, row};
    }
    mBestForSim.assign(mSim.size(), 0);
    mBestForGen.assign(mSim.size(), 0);
    for (const auto& kv : bestOfSim)
      mBestForSim[kv.second.second] = 1;
    for (const auto& kv : bestOfGen)
      mBestForGen[kv.second.second] = 1;

    auto mTable = std::make_unique<nanoaod::FlatTable>(mSim.size(), matchName_, false, false);
    mTable->setDoc("SimJet <-> GenJet pairs sharing energy through the Geant4 ancestry of the SimJet constituents (no geometric matching)");
    mTable->addColumn<int32_t>("simJetIdx", mSim, "row in the SimJet table");
    mTable->addColumn<int32_t>("genJetIdx", mGen, "row in the GenJet table");
    mTable->addColumn<float>("sharedEnergy", mShared, "energy of the SimJet constituents whose generator ancestor is in this GenJet [GeV]", 10);
    mTable->addColumn<float>("simFraction", mSimFrac, "sharedEnergy / SimJet energy: fraction of the SimJet originating from this GenJet", 10);
    mTable->addColumn<float>("genFraction", mGenFrac, "fraction of the GenJet energy whose Geant4 descendants were clustered into this SimJet", 10);
    mTable->addColumn<int32_t>("nShared", mN, "number of SimJet constituents descending from this GenJet");
    mTable->addColumn<float>("dR", mDR, "deltaR between the two jet axes (for reference only)", 10);
    mTable->addColumn<float>("ptRatio", mPtRatio, "SimJet pt / GenJet pt", 10);
    mTable->addColumn<uint8_t>("bestForSim", mBestForSim, "1 if this GenJet has the largest sharedEnergy among the pairs of this SimJet");
    mTable->addColumn<uint8_t>("bestForGen", mBestForGen, "1 if this SimJet has the largest genFraction among the pairs of this GenJet");

    auto cTable = std::make_unique<nanoaod::FlatTable>(cJet.size(), constName_, false, false);
    cTable->setDoc("GenJet constituents");
    cTable->addColumn<int32_t>("genJetIdx", cJet, "row in the GenJet table");
    cTable->addColumn<int32_t>("genPartIdx", cGenPart, "row in the GenPart table (-1 if pruned away)");
    cTable->addColumn<float>("energy", cEnergy, "constituent energy [GeV]", 10);

    event.put(std::move(mTable), "matches");
    if (writeConst_)
      event.put(std::move(cTable), "genConstituents");
  }

private:
  edm::EDGetTokenT<edm::View<reco::Jet>> simJetsToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> simCandsToken_;
  edm::EDGetTokenT<std::vector<int>> simIndexToken_;
  edm::EDGetTokenT<edm::SimTrackContainer> simTracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> simVerticesToken_;
  edm::EDGetTokenT<edm::View<reco::Jet>> genJetsToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genTableToken_;
  std::string matchName_;
  std::string constName_;
  bool writeConst_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimGenJetMatchProducer);
