// Tables of the per-particle calorimeter deposits (SimCalo) and of the ideal
// PF candidates (SimPFCand) made by PicoSimCaloCandidateProducer, with the
// indices of the jets they were clustered into.
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

class PicoSimCaloTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoSimCaloTableProducer(const edm::ParameterSet& cfg)
      : tracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        caloToken_(consumes<reco::GenParticleCollection>(edm::InputTag(cfg.getParameter<std::string>("src"), "calo"))),
        caloIdxToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("src"), "caloSimTrackIndex"))),
        caloNToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("src"), "caloNCells"))),
        pfToken_(consumes<reco::GenParticleCollection>(edm::InputTag(cfg.getParameter<std::string>("src"), "pf"))),
        pfIdxToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("src"), "pfSimTrackIndex"))),
        pfKindToken_(consumes<std::vector<int>>(edm::InputTag(cfg.getParameter<std::string>("src"), "pfKind"))),
        caloJetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("caloJets"))),
        pfJetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("pfJets"))),
        caloName_(cfg.getParameter<std::string>("caloName")),
        pfName_(cfg.getParameter<std::string>("pfName")) {
    const std::string src = cfg.getParameter<std::string>("src");
    for (const char* s : {"caloEcal", "caloEs", "caloHcal", "caloHo", "caloHf"})
      caloEToken_.push_back(consumes<std::vector<float>>(edm::InputTag(src, s)));
    produces<nanoaod::FlatTable>("calo");
    produces<nanoaod::FlatTable>("pf");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<std::string>("src", "picoSimCaloCandidates");
    desc.add<edm::InputTag>("caloJets", edm::InputTag("picoAk4SimCaloJets"));
    desc.add<edm::InputTag>("pfJets", edm::InputTag("picoAk4SimPFJets"));
    desc.add<std::string>("caloName", "SimCalo");
    desc.add<std::string>("pfName", "SimPFCand");
    descriptions.addWithDefaultLabel(desc);
  }

  static std::vector<int32_t> jetOfConstituent(const edm::View<reco::Jet>& jets, size_t n) {
    std::vector<int32_t> out(n, -1);
    for (size_t j = 0; j < jets.size(); ++j)
      for (unsigned d = 0; d < jets[j].numberOfDaughters(); ++d) {
        const auto ptr = jets[j].daughterPtr(d);
        if (ptr.isNonnull() && ptr.key() < n)
          out[ptr.key()] = j;
      }
    return out;
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& calo = event.get(caloToken_);
    const auto& caloIdx = event.get(caloIdxToken_);
    const auto& caloN = event.get(caloNToken_);
    std::vector<const std::vector<float>*> caloE;
    for (const auto& tok : caloEToken_)
      caloE.push_back(&event.get(tok));
    const auto& pf = event.get(pfToken_);
    const auto& pfIdx = event.get(pfIdxToken_);
    const auto& pfKind = event.get(pfKindToken_);
    const auto caloJet = jetOfConstituent(event.get(caloJetsToken_), calo.size());
    const auto pfJet = jetOfConstituent(event.get(pfJetsToken_), pf.size());

    const size_t nC = calo.size();
    std::vector<int32_t> cTrack, cPdg, cCharge, cN, cJet;
    std::vector<float> cE, cPt, cEta, cPhi, cEcal, cEs, cHcal, cHo, cHf, cBoundaryE, cResponse;
    std::unordered_map<int, int32_t> caloRowOfTrack;
    for (size_t i = 0; i < nC; ++i) {
      const int t = caloIdx[i];
      caloRowOfTrack[t] = i;
      cTrack.push_back(t);
      cPdg.push_back(calo[i].pdgId());
      cCharge.push_back(calo[i].charge());
      cE.push_back(calo[i].energy());
      cPt.push_back(calo[i].pt());
      cEta.push_back(calo[i].eta());
      cPhi.push_back(calo[i].phi());
      cEcal.push_back((*caloE[0])[i]);
      cEs.push_back((*caloE[1])[i]);
      cHcal.push_back((*caloE[2])[i]);
      cHo.push_back((*caloE[3])[i]);
      cHf.push_back((*caloE[4])[i]);
      cN.push_back(caloN[i]);
      double eb = -1;
      if (t >= 0 && size_t(t) < tracks.size())
        eb = tracks[t].crossedBoundary() ? tracks[t].getMomentumAtBoundary().E() : tracks[t].momentum().E();
      cBoundaryE.push_back(eb);
      cResponse.push_back(eb > 0 ? calo[i].energy() / eb : -1.f);
      cJet.push_back(caloJet[i]);
    }

    const size_t nP = pf.size();
    std::vector<int32_t> pTrack, pKind, pPdg, pCharge, pCalo, pJet;
    std::vector<float> pPt, pEta, pPhi, pE;
    for (size_t i = 0; i < nP; ++i) {
      const int t = pfIdx[i];
      pTrack.push_back(t);
      pKind.push_back(pfKind[i]);
      pPdg.push_back(pf[i].pdgId());
      pCharge.push_back(pf[i].charge());
      pPt.push_back(pf[i].pt());
      pEta.push_back(pf[i].eta());
      pPhi.push_back(pf[i].phi());
      pE.push_back(pf[i].energy());
      auto it = caloRowOfTrack.find(t);
      pCalo.push_back(it == caloRowOfTrack.end() ? -1 : it->second);
      pJet.push_back(pfJet[i]);
    }

    auto cTable = std::make_unique<nanoaod::FlatTable>(nC, caloName_, false, false);
    cTable->setDoc("calorimeter deposits of the Geant4 sim hits summed per particle that entered the calorimeter (signal event only, GeV-equivalent)");
    cTable->addColumn<int32_t>("simTrackIdx", cTrack, "row in the SimTrack table of the particle that entered the calorimeter");
    cTable->addColumn<int32_t>("pdgId", cPdg, "PDG identifier of that particle");
    cTable->addColumn<int32_t>("charge", cCharge, "electric charge of that particle");
    cTable->addColumn<float>("energy", cE, "total deposit: ECAL + ES + HCAL + HO + HF [GeV-equivalent]", 10);
    cTable->addColumn<float>("pt", cPt, "massless pt of the deposit along its energy-weighted direction", 10);
    cTable->addColumn<float>("eta", cEta, "energy-weighted direction of the deposit", 10);
    cTable->addColumn<float>("phi", cPhi, "energy-weighted direction of the deposit", 10);
    cTable->addColumn<float>("ecalEnergy", cEcal, "EB + EE deposit [GeV]", 10);
    cTable->addColumn<float>("esEnergy", cEs, "preshower deposit [GeV]", 10);
    cTable->addColumn<float>("hcalEnergy", cHcal, "HB + HE deposit, sampling-factor corrected [GeV]", 10);
    cTable->addColumn<float>("hoEnergy", cHo, "HO deposit, sampling-factor corrected [GeV]", 10);
    cTable->addColumn<float>("hfEnergy", cHf, "HF deposit, photoelectrons converted with the HF factors [GeV]", 10);
    cTable->addColumn<int32_t>("nCells", cN, "number of cells above threshold with a deposit of this particle");
    cTable->addColumn<float>("boundaryE", cBoundaryE, "energy of the particle when it entered the calorimeter (production energy if the crossing was not recorded)", 10);
    cTable->addColumn<float>("response", cResponse, "energy / boundaryE: single-particle calorimeter response", 10);
    cTable->addColumn<int32_t>("simCaloJetIdx", cJet, "row in the SimCaloJet table (-1: not clustered)");

    auto pTable = std::make_unique<nanoaod::FlatTable>(nP, pfName_, false, false);
    pTable->setDoc("ideal particle-flow candidates: terminal Geant4 particles (no decay/conversion stored), charged and trackable from their momentum, the others from their calorimeter deposit");
    pTable->addColumn<int32_t>("simTrackIdx", pTrack, "row in the SimTrack table");
    pTable->addColumn<int32_t>("kind", pKind, "1 charged from momentum, 2 neutral from deposit, 3 charged but not trackable (born outside the tracker volume, outside the acceptance or below the pt cut) from deposit");
    pTable->addColumn<int32_t>("pdgId", pPdg, "PDG identifier");
    pTable->addColumn<int32_t>("charge", pCharge, "electric charge");
    pTable->addColumn<float>("pt", pPt, "pt", 10);
    pTable->addColumn<float>("eta", pEta, "eta", 10);
    pTable->addColumn<float>("phi", pPhi, "phi", 10);
    pTable->addColumn<float>("energy", pE, "energy", 10);
    pTable->addColumn<int32_t>("simCaloIdx", pCalo, "row in the " + caloName_ + " table of this particle's deposit (-1: none)");
    pTable->addColumn<int32_t>("simPFJetIdx", pJet, "row in the SimPFJet table (-1: not clustered)");

    event.put(std::move(cTable), "calo");
    event.put(std::move(pTable), "pf");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> caloToken_;
  edm::EDGetTokenT<std::vector<int>> caloIdxToken_, caloNToken_;
  std::vector<edm::EDGetTokenT<std::vector<float>>> caloEToken_;
  edm::EDGetTokenT<reco::GenParticleCollection> pfToken_;
  edm::EDGetTokenT<std::vector<int>> pfIdxToken_, pfKindToken_;
  edm::EDGetTokenT<edm::View<reco::Jet>> caloJetsToken_, pfJetsToken_;
  std::string caloName_, pfName_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimCaloTableProducer);
