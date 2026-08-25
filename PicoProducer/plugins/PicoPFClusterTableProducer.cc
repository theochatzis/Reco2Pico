#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/ParticleFlowReco/interface/PFCluster.h"
#include "DataFormats/ParticleFlowReco/interface/PFClusterFwd.h"

class PicoPFClusterTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoPFClusterTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<reco::PFClusterCollection>(cfg.getParameter<edm::InputTag>("src"))),
        name_(cfg.getParameter<std::string>("name")),
        minEnergy_(cfg.getParameter<double>("minEnergy")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<reco::PFClusterCollection> clusters;
    event.getByToken(srcToken_, clusters);

    std::vector<float> energy, pt, eta, phi, x, y, z, depth, time, timeError;
    std::vector<int32_t> layer, nHits, algo;
    std::vector<uint32_t> seedRawId, flags;

    for (const auto& cluster : *clusters) {
      if (cluster.energy() < minEnergy_)
        continue;
      energy.push_back(cluster.energy());
      pt.push_back(cluster.pt());
      eta.push_back(cluster.eta());
      phi.push_back(cluster.phi());
      x.push_back(cluster.x()); y.push_back(cluster.y()); z.push_back(cluster.z());
      layer.push_back(static_cast<int32_t>(cluster.layer()));
      depth.push_back(cluster.depth());
      time.push_back(cluster.time());
      timeError.push_back(cluster.timeError());
      nHits.push_back(static_cast<int32_t>(cluster.size()));
      seedRawId.push_back(cluster.seed().rawId());
      algo.push_back(static_cast<int32_t>(cluster.algo()));
      flags.push_back(cluster.flags());
    }

    auto table = std::make_unique<nanoaod::FlatTable>(energy.size(), name_, false, false);
    table->setDoc("reco::PFCluster table");
    table->addColumn<float>("energy", energy, "cluster energy", 10);
    table->addColumn<float>("pt", pt, "massless transverse momentum from cluster position", 10);
    table->addColumn<float>("eta", eta, "cluster position pseudorapidity", 10);
    table->addColumn<float>("phi", phi, "cluster position azimuth", 10);
    table->addColumn<float>("x", x, "cluster centroid x", 10);
    table->addColumn<float>("y", y, "cluster centroid y", 10);
    table->addColumn<float>("z", z, "cluster centroid z", 10);
    table->addColumn<int32_t>("layer", layer, "PFLayer::Layer enum value");
    table->addColumn<float>("depth", depth, "cluster depth", 10);
    table->addColumn<float>("time", time, "cluster time", 10);
    table->addColumn<float>("timeError", timeError, "cluster time uncertainty", 10);
    table->addColumn<int32_t>("nHits", nHits, "number of DetId/fraction entries in cluster");
    table->addColumn<uint32_t>("seedRawId", seedRawId, "raw DetId of cluster seed");
    table->addColumn<int32_t>("algo", algo, "CaloCluster algorithm enum value");
    table->addColumn<uint32_t>("flags", flags, "CaloCluster flags");

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<reco::PFClusterCollection> srcToken_;
  std::string name_;
  double minEnergy_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoPFClusterTableProducer);
