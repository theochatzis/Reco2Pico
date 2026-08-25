#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidate.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidateFwd.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"

class PicoRecoPFCandidateTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoRecoPFCandidateTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<reco::PFCandidateCollection>(cfg.getParameter<edm::InputTag>("src"))),
        trackToken_(consumes<reco::TrackCollection>(cfg.getParameter<edm::InputTag>("tracks"))),
        vertexToken_(consumes<reco::VertexCollection>(cfg.getParameter<edm::InputTag>("vertices"))),
        name_(cfg.getParameter<std::string>("name")),
        minPt_(cfg.getParameter<double>("minPt")),
        trackTableMinPt_(cfg.getParameter<double>("trackTableMinPt")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<reco::PFCandidateCollection> cands;
    edm::Handle<reco::TrackCollection> tracks;
    edm::Handle<reco::VertexCollection> vertices;
    event.getByToken(srcToken_, cands);
    event.getByToken(trackToken_, tracks);
    event.getByToken(vertexToken_, vertices);

    const reco::Vertex* pv = vertices->empty() ? nullptr : &vertices->front();

    // Map the original reco::Track collection index to the row number in the
    // possibly pT-filtered Pico Track table. This keeps PFCand_trackIdx valid
    // when trackMinPt > 0.
    std::vector<int32_t> trackRowIndex(tracks->size(), -1);
    int32_t trackRow = 0;
    for (size_t i = 0; i < tracks->size(); ++i) {
      if ((*tracks)[i].pt() < trackTableMinPt_)
        continue;
      trackRowIndex[i] = trackRow++;
    }

    std::vector<float> pt, eta, phi, mass;
    std::vector<int32_t> charge, pdgId, particleId;
    std::vector<float> vx, vy, vz;
    std::vector<float> ecalEnergy, rawEcalEnergy, hcalEnergy, rawHcalEnergy, hoEnergy, rawHoEnergy;
    std::vector<float> time, timeError;
    std::vector<uint8_t> hasTrack;
    std::vector<int32_t> trackIdx, trkAlgo, trkOriginalAlgo, trkQualityMask;
    std::vector<float> trkDxy, trkDz, trkDxyErr, trkDzErr;
    std::vector<int32_t> trkNValidHits, trkNPixelHits;

    const auto reserve = cands->size();
    pt.reserve(reserve); eta.reserve(reserve); phi.reserve(reserve); mass.reserve(reserve);
    charge.reserve(reserve); pdgId.reserve(reserve); particleId.reserve(reserve);
    vx.reserve(reserve); vy.reserve(reserve); vz.reserve(reserve);
    ecalEnergy.reserve(reserve); rawEcalEnergy.reserve(reserve);
    hcalEnergy.reserve(reserve); rawHcalEnergy.reserve(reserve);
    hoEnergy.reserve(reserve); rawHoEnergy.reserve(reserve);
    time.reserve(reserve); timeError.reserve(reserve);
    hasTrack.reserve(reserve); trackIdx.reserve(reserve);
    trkAlgo.reserve(reserve); trkOriginalAlgo.reserve(reserve); trkQualityMask.reserve(reserve);
    trkDxy.reserve(reserve); trkDz.reserve(reserve); trkDxyErr.reserve(reserve); trkDzErr.reserve(reserve);
    trkNValidHits.reserve(reserve); trkNPixelHits.reserve(reserve);

    for (const auto& cand : *cands) {
      if (cand.pt() < minPt_)
        continue;

      pt.push_back(cand.pt());
      eta.push_back(cand.eta());
      phi.push_back(cand.phi());
      mass.push_back(cand.mass());
      charge.push_back(cand.charge());
      pdgId.push_back(cand.pdgId());
      particleId.push_back(static_cast<int32_t>(cand.particleId()));
      vx.push_back(cand.vx());
      vy.push_back(cand.vy());
      vz.push_back(cand.vz());
      ecalEnergy.push_back(cand.ecalEnergy());
      rawEcalEnergy.push_back(cand.rawEcalEnergy());
      hcalEnergy.push_back(cand.hcalEnergy());
      rawHcalEnergy.push_back(cand.rawHcalEnergy());
      hoEnergy.push_back(cand.hoEnergy());
      rawHoEnergy.push_back(cand.rawHoEnergy());
      time.push_back(cand.time());
      timeError.push_back(cand.timeError());

      const auto ref = cand.trackRef();
      const bool validTrack = ref.isNonnull() && ref.isAvailable();
      hasTrack.push_back(validTrack ? 1 : 0);

      int32_t idx = -1;
      int32_t algo = -1;
      int32_t originalAlgo = -1;
      int32_t qualityMask = 0;
      float dxy = 999.f, dz = 999.f, dxyErr = 999.f, dzErr = 999.f;
      int32_t nValidHits = 0, nPixelHits = 0;

      if (validTrack) {
        if (ref.id() == tracks.id() && ref.key() < tracks->size())
          idx = trackRowIndex[ref.key()];

        algo = static_cast<int32_t>(ref->algo());
        originalAlgo = static_cast<int32_t>(ref->originalAlgo());
        qualityMask = ref->qualityMask();
        dxy = pv ? ref->dxy(pv->position()) : ref->dxy();
        dz = pv ? ref->dz(pv->position()) : ref->dz();
        dxyErr = ref->dxyError();
        dzErr = ref->dzError();
        nValidHits = ref->numberOfValidHits();
        nPixelHits = ref->hitPattern().numberOfValidPixelHits();
      }

      trackIdx.push_back(idx);
      trkAlgo.push_back(algo);
      trkOriginalAlgo.push_back(originalAlgo);
      trkQualityMask.push_back(qualityMask);
      trkDxy.push_back(dxy);
      trkDz.push_back(dz);
      trkDxyErr.push_back(dxyErr);
      trkDzErr.push_back(dzErr);
      trkNValidHits.push_back(nValidHits);
      trkNPixelHits.push_back(nPixelHits);
    }

    auto table = std::make_unique<nanoaod::FlatTable>(pt.size(), name_, false, false);
    table->setDoc("reco::PFCandidate table");
    table->addColumn<float>("pt", pt, "transverse momentum", 10);
    table->addColumn<float>("eta", eta, "pseudorapidity", 10);
    table->addColumn<float>("phi", phi, "azimuth", 10);
    table->addColumn<float>("mass", mass, "mass", 10);
    table->addColumn<int32_t>("charge", charge, "electric charge");
    table->addColumn<int32_t>("pdgId", pdgId, "PDG identifier");
    table->addColumn<int32_t>("particleId", particleId, "reco::PFCandidate::ParticleType enum value");
    table->addColumn<float>("vx", vx, "candidate vertex x", 10);
    table->addColumn<float>("vy", vy, "candidate vertex y", 10);
    table->addColumn<float>("vz", vz, "candidate vertex z", 10);
    table->addColumn<float>("ecalEnergy", ecalEnergy, "corrected ECAL energy", 10);
    table->addColumn<float>("rawEcalEnergy", rawEcalEnergy, "raw ECAL energy", 10);
    table->addColumn<float>("hcalEnergy", hcalEnergy, "corrected HCAL energy", 10);
    table->addColumn<float>("rawHcalEnergy", rawHcalEnergy, "raw HCAL energy", 10);
    table->addColumn<float>("hoEnergy", hoEnergy, "corrected HO energy", 10);
    table->addColumn<float>("rawHoEnergy", rawHoEnergy, "raw HO energy", 10);
    table->addColumn<float>("time", time, "PF candidate time", 10);
    table->addColumn<float>("timeError", timeError, "PF candidate time uncertainty", 10);
    table->addColumn<uint8_t>("hasTrack", hasTrack, "1 if a reco::TrackRef is available");
    table->addColumn<int32_t>("trackIdx", trackIdx, "index into Track table when TrackRef points to configured track collection; -1 otherwise");
    table->addColumn<int32_t>("trkAlgo", trkAlgo, "TrackBase::TrackAlgorithm enum value; -1 without track");
    table->addColumn<int32_t>("trkOriginalAlgo", trkOriginalAlgo, "original TrackAlgorithm enum value; -1 without track");
    table->addColumn<int32_t>("trkQualityMask", trkQualityMask, "track quality bit mask");
    table->addColumn<float>("trkDxy", trkDxy, "track dxy relative to first configured vertex", 10);
    table->addColumn<float>("trkDz", trkDz, "track dz relative to first configured vertex", 10);
    table->addColumn<float>("trkDxyErr", trkDxyErr, "track dxy uncertainty", 10);
    table->addColumn<float>("trkDzErr", trkDzErr, "track dz uncertainty", 10);
    table->addColumn<int32_t>("trkNValidHits", trkNValidHits, "number of valid hits on associated track");
    table->addColumn<int32_t>("trkNPixelHits", trkNPixelHits, "number of valid pixel hits on associated track");

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<reco::PFCandidateCollection> srcToken_;
  edm::EDGetTokenT<reco::TrackCollection> trackToken_;
  edm::EDGetTokenT<reco::VertexCollection> vertexToken_;
  std::string name_;
  double minPt_;
  double trackTableMinPt_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoRecoPFCandidateTableProducer);
