// Ancestry-based matching of reconstructed PF jets to gen jets, through the
// attribution of their PF constituents to simulated particles
// (PicoPFCandTruthProducer) and the Geant4 ancestry of those particles.
//
// For a (reco jet j, gen jet g) pair:
//   sharedEnergy = sum over the constituents of j (with their clustering
//                  weight) of the energy attributed to particles descending
//                  from constituents of g
//   recoFraction = sharedEnergy / E(j)
//   genFraction  = sum over the constituents p of g of E(p) * f_j(p) / E(g),
//                  f_j(p) = (descendant energy of p found in j) /
//                           (descendant energy of p found in any PF candidate)
// Per reco jet also the signal energy/pt (attributed to any signal particle)
// and the unattributed (pile-up) fraction.
//
// Tables: <name>GenMatch (instance "matches"), <name>Const (instance "constituents")
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

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/JetReco/interface/Jet.h"
#include "DataFormats/Math/interface/deltaR.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidate.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidateFwd.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoSimAncestry.h"

class PicoRecoJetGenMatchProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoRecoJetGenMatchProducer(const edm::ParameterSet& cfg)
      : jetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("jets"))),
        candsToken_(consumes<reco::PFCandidateCollection>(cfg.getParameter<edm::InputTag>("candidates"))),
        weightsToken_(mayConsume<edm::ValueMap<float>>(cfg.getParameter<edm::InputTag>("weights"))),
        useWeights_(!cfg.getParameter<edm::InputTag>("weights").label().empty()),
        shareCandToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("truth"), "shareCand"))),
        shareSimToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("truth"), "shareSimTrack"))),
        shareEToken_(consumes<std::vector<float>>(edm::InputTag(cfg.getParameter<std::string>("truth"), "shareEnergy"))),
        simTracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        simVerticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        genJetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("genJets"))),
        genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genParticles"))),
        name_(cfg.getParameter<std::string>("name")),
        candMinPt_(cfg.getParameter<double>("candMinPt")) {
    produces<nanoaod::FlatTable>("matches");
    produces<nanoaod::FlatTable>("constituents");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("jets", edm::InputTag("picoAk4PFJets"));
    desc.add<edm::InputTag>("candidates", edm::InputTag("particleFlow"));
    desc.add<edm::InputTag>("weights", edm::InputTag(""));
    desc.add<std::string>("truth", "picoPFCandTruthTable");
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("genJets", edm::InputTag("picoAk4GenJetsNoNu"));
    desc.add<edm::InputTag>("genParticles", edm::InputTag("genParticles"));
    desc.add<std::string>("name", "PFJet");
    desc.add<double>("candMinPt", 0.0);
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& jets = event.get(jetsToken_);
    edm::Handle<reco::PFCandidateCollection> candsHandle;
    event.getByToken(candsToken_, candsHandle);
    const auto& cands = *candsHandle;
    edm::Handle<edm::ValueMap<float>> weights;
    if (useWeights_)
      event.getByToken(weightsToken_, weights);
    const auto& shareCand = event.get(shareCandToken_);
    const auto& shareSim = event.get(shareSimToken_);
    const auto& shareE = event.get(shareEToken_);
    const auto& tracks = event.get(simTracksToken_);
    const auto& vertices = event.get(simVerticesToken_);
    const auto& genJets = event.get(genJetsToken_);
    edm::Handle<reco::GenParticleCollection> gensHandle;
    event.getByToken(genToken_, gensHandle);
    const auto& gens = *gensHandle;

    const std::vector<int> ancestor = pico::ancestorGenParticle(tracks, vertices, gens);
    const std::vector<int> genJetOf = pico::genJetOfParticle(genJets, gensHandle);

    // shares per PF candidate: (gen ancestor index, energy)
    std::vector<std::vector<std::pair<int, float>>> candShares(cands.size());
    for (size_t i = 0; i < shareCand.size(); ++i) {
      const int c = shareCand[i], t = shareSim[i];
      if (c < 0 || size_t(c) >= cands.size() || t < 0 || size_t(t) >= tracks.size())
        continue;
      candShares[c].emplace_back(ancestor[t], shareE[i]);
    }
    // total reconstructed descendant energy per gen particle (all candidates)
    std::unordered_map<int, double> descTotal;
    for (const auto& v : candShares)
      for (const auto& s : v)
        if (s.first >= 0)
          descTotal[s.first] += s.second;

    std::vector<int32_t> candRow(cands.size(), -1);
    for (size_t i = 0, r = 0; i < cands.size(); ++i)
      if (cands[i].pt() >= candMinPt_)
        candRow[i] = r++;

    auto resolve = [&](edm::Ptr<reco::Candidate> ptr) -> int {
      for (int depth = 0; depth < 4 && ptr.isNonnull(); ++depth) {
        if (ptr.id() == candsHandle.id())
          return ptr.key();
        if (!ptr.isAvailable())
          return -1;
        const reco::Candidate* obj = ptr.get();
        if (obj >= &cands.front() && obj <= &cands.back())
          return static_cast<int>(static_cast<const reco::PFCandidate*>(obj) - &cands.front());
        if (obj->numberOfSourceCandidatePtrs() == 0)
          return -1;
        ptr = obj->sourceCandidatePtr(0);
      }
      return -1;
    };

    std::vector<int32_t> kJet, kCand;
    std::vector<float> kWeight;
    struct Pair {
      double shared = 0, genShared = 0;
      int n = 0;
    };
    std::map<std::pair<int, int>, Pair> pairs;
    std::map<std::pair<int, int>, double> descInJet;  // (gen k, jet j)
    std::vector<double> jetSignalE(jets.size(), 0), jetSignalPx(jets.size(), 0), jetSignalPy(jets.size(), 0);
    for (size_t j = 0; j < jets.size(); ++j) {
      const reco::Jet& jet = jets[j];
      for (unsigned d = 0; d < jet.numberOfDaughters(); ++d) {
        const auto ptr = jet.daughterPtr(d);
        const int c = resolve(ptr);
        if (c < 0)
          continue;
        float w = 1.f;
        if (useWeights_ && weights.isValid()) {
          edm::Ptr<reco::PFCandidate> pfPtr(candsHandle, c);
          w = (*weights)[pfPtr];
        }
        kJet.push_back(j);
        kCand.push_back(candRow[c]);
        kWeight.push_back(w);
        const auto& cand = cands[c];
        for (const auto& s : candShares[c]) {
          const double e = s.second * w;
          jetSignalE[j] += e;
          const double f = cand.energy() > 0 ? e / cand.energy() : 0;
          jetSignalPx[j] += f * cand.px();
          jetSignalPy[j] += f * cand.py();
          if (s.first < 0)
            continue;
          descInJet[{s.first, j}] += e;
          const int g = genJetOf[s.first];
          if (g < 0)
            continue;
          auto& p = pairs[{j, g}];
          p.shared += e;
          p.n += 1;
        }
      }
    }
    for (const auto& kv : descInJet) {
      const int k = kv.first.first, j = kv.first.second, g = genJetOf[k];
      if (g < 0)
        continue;
      const double tot = descTotal[k];
      if (tot > 0)
        pairs[{j, g}].genShared += gens[k].energy() * kv.second / tot;
    }

    std::vector<int32_t> mJet, mGen, mN;
    std::vector<float> mShared, mRecoFrac, mGenFrac, mDR, mPtRatio, mSignalPtRatio;
    std::vector<uint8_t> mBestForReco, mBestForGen;
    std::map<int, std::pair<double, size_t>> bestOfReco, bestOfGen;
    for (const auto& kv : pairs) {
      const int j = kv.first.first, g = kv.first.second;
      const double ej = jets[j].energy(), eg = genJets[g].energy();
      mJet.push_back(j);
      mGen.push_back(g);
      mN.push_back(kv.second.n);
      mShared.push_back(kv.second.shared);
      mRecoFrac.push_back(ej > 0 ? kv.second.shared / ej : 0.f);
      mGenFrac.push_back(eg > 0 ? kv.second.genShared / eg : 0.f);
      mDR.push_back(reco::deltaR(jets[j], genJets[g]));
      mPtRatio.push_back(genJets[g].pt() > 0 ? jets[j].pt() / genJets[g].pt() : 0.f);
      mSignalPtRatio.push_back(genJets[g].pt() > 0 ? std::hypot(jetSignalPx[j], jetSignalPy[j]) / genJets[g].pt() : 0.f);
      const size_t row = mJet.size() - 1;
      if (!bestOfReco.count(j) || kv.second.shared > bestOfReco[j].first)
        bestOfReco[j] = {kv.second.shared, row};
      if (!bestOfGen.count(g) || kv.second.genShared > bestOfGen[g].first)
        bestOfGen[g] = {kv.second.genShared, row};
    }
    mBestForReco.assign(mJet.size(), 0);
    mBestForGen.assign(mJet.size(), 0);
    for (const auto& kv : bestOfReco)
      mBestForReco[kv.second.second] = 1;
    for (const auto& kv : bestOfGen)
      mBestForGen[kv.second.second] = 1;

    auto mTable = std::make_unique<nanoaod::FlatTable>(mJet.size(), name_ + "GenMatch", false, false);
    mTable->setDoc(name_ + " <-> GenJet pairs sharing energy through the attribution of the PF constituents to simulated particles and their Geant4 ancestry");
    mTable->addColumn<int32_t>("jetIdx", mJet, "row in the " + name_ + " table");
    mTable->addColumn<int32_t>("genJetIdx", mGen, "row in the GenJet table");
    mTable->addColumn<float>("sharedEnergy", mShared, "energy of the jet constituents attributed to particles descending from this GenJet [GeV]", 10);
    mTable->addColumn<float>("recoFraction", mRecoFrac, "sharedEnergy / jet energy", 10);
    mTable->addColumn<float>("genFraction", mGenFrac, "fraction of the GenJet energy whose reconstructed descendants are in this jet", 10);
    mTable->addColumn<int32_t>("nShared", mN, "number of (constituent, particle) shares from this GenJet");
    mTable->addColumn<float>("dR", mDR, "deltaR between the two jet axes (for reference only)", 10);
    mTable->addColumn<float>("ptRatio", mPtRatio, "jet pt / GenJet pt", 10);
    mTable->addColumn<float>("signalPtRatio", mSignalPtRatio, "pt of the signal-attributed part of the jet / GenJet pt (pile-up removed by attribution)", 10);
    mTable->addColumn<uint8_t>("bestForReco", mBestForReco, "1 if this GenJet has the largest sharedEnergy among the pairs of this jet");
    mTable->addColumn<uint8_t>("bestForGen", mBestForGen, "1 if this jet has the largest genFraction among the pairs of this GenJet");

    auto kTable = std::make_unique<nanoaod::FlatTable>(kJet.size(), name_ + "Const", false, false);
    kTable->setDoc(name_ + " constituents");
    kTable->addColumn<int32_t>("jetIdx", kJet, "row in the " + name_ + " table");
    kTable->addColumn<int32_t>("pfCandIdx", kCand, "row in the PFCand table (-1: filtered out)");
    kTable->addColumn<float>("weight", kWeight, "clustering weight of the constituent (puppi), 1 otherwise", 10);

    // per-jet signal content goes into the constituent-less summary columns of the match table rows;
    // the jet table itself is written by SimplePFJetFlatTableProducer in python
    event.put(std::move(mTable), "matches");
    event.put(std::move(kTable), "constituents");
  }

private:
  edm::EDGetTokenT<edm::View<reco::Jet>> jetsToken_;
  edm::EDGetTokenT<reco::PFCandidateCollection> candsToken_;
  edm::EDGetTokenT<edm::ValueMap<float>> weightsToken_;
  bool useWeights_;
  edm::EDGetTokenT<std::vector<int>> shareCandToken_, shareSimToken_;
  edm::EDGetTokenT<std::vector<float>> shareEToken_;
  edm::EDGetTokenT<edm::SimTrackContainer> simTracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> simVerticesToken_;
  edm::EDGetTokenT<edm::View<reco::Jet>> genJetsToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  std::string name_;
  double candMinPt_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoRecoJetGenMatchProducer);
