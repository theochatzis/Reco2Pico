#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"

class PicoTrackTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoTrackTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<reco::TrackCollection>(cfg.getParameter<edm::InputTag>("src"))),
        vertexToken_(consumes<reco::VertexCollection>(cfg.getParameter<edm::InputTag>("vertices"))),
        name_(cfg.getParameter<std::string>("name")),
        minPt_(cfg.getParameter<double>("minPt")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<reco::TrackCollection> tracks;
    edm::Handle<reco::VertexCollection> vertices;
    event.getByToken(srcToken_, tracks);
    event.getByToken(vertexToken_, vertices);

    const reco::Vertex* pv = vertices->empty() ? nullptr : &vertices->front();

    // For each configured track, identify the vertex where it has the largest fit weight.
    std::vector<int32_t> bestVertex(tracks->size(), -1);
    std::vector<float> bestWeight(tracks->size(), 0.f);
    for (size_t iv = 0; iv < vertices->size(); ++iv) {
      const auto& vertex = (*vertices)[iv];
      for (const auto& ref : vertex.tracks()) {
        if (ref.isNull() || !ref.isAvailable() || ref.id() != tracks.id() || ref.key() >= tracks->size())
          continue;
        const float weight = vertex.trackWeight(ref);
        if (weight > bestWeight[ref.key()]) {
          bestWeight[ref.key()] = weight;
          bestVertex[ref.key()] = static_cast<int32_t>(iv);
        }
      }
    }

    std::vector<float> pt, eta, phi, p, ptErr;
    std::vector<int32_t> charge;
    std::vector<float> vx, vy, vz, dxy, dz, dxyErr, dzErr;
    std::vector<float> chi2, ndof, normalizedChi2;
    std::vector<int32_t> algo, originalAlgo, qualityMask, stopReason;
    std::vector<uint64_t> algoMask;
    std::vector<uint8_t> highPurity;
    std::vector<int32_t> nValidHits, nLostHits, nPixelHits, nStripHits, nTrackerLayers, nPixelLayers;
    std::vector<int32_t> pvIdx;
    std::vector<float> pvWeight;

    for (size_t i = 0; i < tracks->size(); ++i) {
      const auto& trk = (*tracks)[i];
      if (trk.pt() < minPt_)
        continue;

      pt.push_back(trk.pt()); eta.push_back(trk.eta()); phi.push_back(trk.phi()); p.push_back(trk.p());
      ptErr.push_back(trk.ptError()); charge.push_back(trk.charge());
      vx.push_back(trk.vx()); vy.push_back(trk.vy()); vz.push_back(trk.vz());
      dxy.push_back(pv ? trk.dxy(pv->position()) : trk.dxy());
      dz.push_back(pv ? trk.dz(pv->position()) : trk.dz());
      dxyErr.push_back(trk.dxyError()); dzErr.push_back(trk.dzError());
      chi2.push_back(trk.chi2()); ndof.push_back(trk.ndof()); normalizedChi2.push_back(trk.normalizedChi2());
      algo.push_back(static_cast<int32_t>(trk.algo()));
      originalAlgo.push_back(static_cast<int32_t>(trk.originalAlgo()));
      algoMask.push_back(trk.algoMaskUL());
      qualityMask.push_back(trk.qualityMask());
      stopReason.push_back(static_cast<int32_t>(trk.stopReason()));
      highPurity.push_back(trk.quality(reco::TrackBase::highPurity) ? 1 : 0);
      nValidHits.push_back(trk.numberOfValidHits());
      nLostHits.push_back(trk.numberOfLostHits());
      nPixelHits.push_back(trk.hitPattern().numberOfValidPixelHits());
      nStripHits.push_back(trk.hitPattern().numberOfValidStripHits());
      nTrackerLayers.push_back(trk.hitPattern().trackerLayersWithMeasurement());
      nPixelLayers.push_back(trk.hitPattern().pixelLayersWithMeasurement());
      pvIdx.push_back(bestVertex[i]);
      pvWeight.push_back(bestWeight[i]);
    }

    auto table = std::make_unique<nanoaod::FlatTable>(pt.size(), name_, false, false);
    table->setDoc("reco::Track table");
    table->addColumn<float>("pt", pt, "transverse momentum", 10);
    table->addColumn<float>("eta", eta, "pseudorapidity", 10);
    table->addColumn<float>("phi", phi, "azimuth", 10);
    table->addColumn<float>("p", p, "momentum magnitude", 10);
    table->addColumn<float>("ptErr", ptErr, "transverse momentum uncertainty", 10);
    table->addColumn<int32_t>("charge", charge, "electric charge");
    table->addColumn<float>("vx", vx, "track reference point x", 10);
    table->addColumn<float>("vy", vy, "track reference point y", 10);
    table->addColumn<float>("vz", vz, "track reference point z", 10);
    table->addColumn<float>("dxy", dxy, "dxy relative to first configured vertex", 10);
    table->addColumn<float>("dz", dz, "dz relative to first configured vertex", 10);
    table->addColumn<float>("dxyErr", dxyErr, "dxy uncertainty", 10);
    table->addColumn<float>("dzErr", dzErr, "dz uncertainty", 10);
    table->addColumn<float>("chi2", chi2, "track fit chi2", 10);
    table->addColumn<float>("ndof", ndof, "track fit ndof", 10);
    table->addColumn<float>("normalizedChi2", normalizedChi2, "track fit chi2/ndof", 10);
    table->addColumn<int32_t>("algo", algo, "TrackAlgorithm enum value");
    table->addColumn<int32_t>("originalAlgo", originalAlgo, "original TrackAlgorithm enum value");
    table->addColumn<uint64_t>("algoMask", algoMask, "bit mask of tracking algorithms associated with track");
    table->addColumn<int32_t>("qualityMask", qualityMask, "track quality bit mask");
    table->addColumn<uint8_t>("highPurity", highPurity, "highPurity track quality flag");
    table->addColumn<int32_t>("stopReason", stopReason, "tracking stop reason enum value");
    table->addColumn<int32_t>("nValidHits", nValidHits, "number of valid hits");
    table->addColumn<int32_t>("nLostHits", nLostHits, "number of lost hits");
    table->addColumn<int32_t>("nPixelHits", nPixelHits, "number of valid pixel hits");
    table->addColumn<int32_t>("nStripHits", nStripHits, "number of valid strip hits");
    table->addColumn<int32_t>("nTrackerLayers", nTrackerLayers, "tracker layers with measurement");
    table->addColumn<int32_t>("nPixelLayers", nPixelLayers, "pixel layers with measurement");
    table->addColumn<int32_t>("pvIdx", pvIdx, "index of Vertex with largest track fit weight; -1 if none");
    table->addColumn<float>("pvWeight", pvWeight, "track weight in Vertex[pvIdx]", 10);

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<reco::TrackCollection> srcToken_;
  edm::EDGetTokenT<reco::VertexCollection> vertexToken_;
  std::string name_;
  double minPt_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoTrackTableProducer);
