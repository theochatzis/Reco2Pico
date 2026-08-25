#include <cmath>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/EcalRecHit/interface/EcalRecHitCollections.h"
#include "DataFormats/EcalDetId/interface/EBDetId.h"
#include "DataFormats/EcalDetId/interface/EEDetId.h"
#include "DataFormats/EcalDetId/interface/EcalSubdetector.h"
#include "DataFormats/HcalRecHit/interface/HcalRecHitCollections.h"
#include "DataFormats/HcalDetId/interface/HcalDetId.h"

class PicoEcalRecHitTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoEcalRecHitTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<EcalRecHitCollection>(cfg.getParameter<edm::InputTag>("src"))),
        name_(cfg.getParameter<std::string>("name")),
        minAbsEnergy_(cfg.getParameter<double>("minAbsEnergy")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<EcalRecHitCollection> hits;
    event.getByToken(srcToken_, hits);

    std::vector<uint32_t> rawId, flags;
    std::vector<int32_t> subdet, ieta, iphi, ix, iy, zside;
    std::vector<float> energy, time, timeError, chi2, energyError;

    for (const auto& hit : *hits) {
      if (std::abs(hit.energy()) < minAbsEnergy_)
        continue;

      const DetId id = hit.id();
      rawId.push_back(id.rawId());
      subdet.push_back(id.subdetId());
      energy.push_back(hit.energy());
      time.push_back(hit.time());
      timeError.push_back(hit.timeError());
      chi2.push_back(hit.chi2());
      energyError.push_back(hit.energyError());
      flags.push_back(hit.flagsBits());

      int32_t outIeta = 0, outIphi = 0, outIx = 0, outIy = 0, outZside = 0;
      if (id.subdetId() == EcalBarrel) {
        const EBDetId eb(id);
        outIeta = eb.ieta();
        outIphi = eb.iphi();
      } else if (id.subdetId() == EcalEndcap) {
        const EEDetId ee(id);
        outIx = ee.ix();
        outIy = ee.iy();
        outZside = ee.zside();
      }
      ieta.push_back(outIeta); iphi.push_back(outIphi);
      ix.push_back(outIx); iy.push_back(outIy); zside.push_back(outZside);
    }

    auto table = std::make_unique<nanoaod::FlatTable>(energy.size(), name_, false, false);
    table->setDoc("ECAL RecHit table");
    table->addColumn<uint32_t>("rawId", rawId, "DetId raw identifier");
    table->addColumn<int32_t>("subdet", subdet, "ECAL subdetector identifier");
    table->addColumn<float>("energy", energy, "RecHit energy", 10);
    table->addColumn<float>("time", time, "RecHit time", 10);
    table->addColumn<float>("timeError", timeError, "RecHit time uncertainty", 10);
    table->addColumn<float>("chi2", chi2, "RecHit reconstruction chi2", 10);
    table->addColumn<float>("energyError", energyError, "RecHit energy uncertainty", 10);
    table->addColumn<uint32_t>("flags", flags, "ECAL RecHit flag bits");
    table->addColumn<int32_t>("ieta", ieta, "EB ieta; 0 outside EB");
    table->addColumn<int32_t>("iphi", iphi, "EB iphi; 0 outside EB");
    table->addColumn<int32_t>("ix", ix, "EE ix; 0 outside EE");
    table->addColumn<int32_t>("iy", iy, "EE iy; 0 outside EE");
    table->addColumn<int32_t>("zside", zside, "EE z side; 0 outside EE");

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<EcalRecHitCollection> srcToken_;
  std::string name_;
  double minAbsEnergy_;
};

template <typename Collection>
class PicoHcalRecHitTableProducerT : public edm::stream::EDProducer<> {
public:
  explicit PicoHcalRecHitTableProducerT(const edm::ParameterSet& cfg)
      : srcToken_(this->template consumes<Collection>(cfg.getParameter<edm::InputTag>("src"))),
        name_(cfg.getParameter<std::string>("name")),
        minAbsEnergy_(cfg.getParameter<double>("minAbsEnergy")) {
    this->template produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<Collection> hits;
    event.getByToken(srcToken_, hits);

    std::vector<uint32_t> rawId;
    std::vector<int32_t> subdet, ieta, iphi, depth;
    std::vector<float> energy, time;

    for (const auto& hit : *hits) {
      if (std::abs(hit.energy()) < minAbsEnergy_)
        continue;
      const HcalDetId id(hit.id());
      rawId.push_back(id.rawId());
      subdet.push_back(static_cast<int32_t>(id.subdet()));
      ieta.push_back(id.ieta());
      iphi.push_back(id.iphi());
      depth.push_back(id.depth());
      energy.push_back(hit.energy());
      time.push_back(hit.time());
    }

    auto table = std::make_unique<nanoaod::FlatTable>(energy.size(), name_, false, false);
    table->setDoc("HCAL RecHit table");
    table->addColumn<uint32_t>("rawId", rawId, "DetId raw identifier");
    table->addColumn<int32_t>("subdet", subdet, "HCAL subdetector enum value");
    table->addColumn<int32_t>("ieta", ieta, "HCAL ieta");
    table->addColumn<int32_t>("iphi", iphi, "HCAL iphi");
    table->addColumn<int32_t>("depth", depth, "HCAL depth");
    table->addColumn<float>("energy", energy, "RecHit energy", 10);
    table->addColumn<float>("time", time, "RecHit time", 10);

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<Collection> srcToken_;
  std::string name_;
  double minAbsEnergy_;
};

using PicoHBHERecHitTableProducer = PicoHcalRecHitTableProducerT<HBHERecHitCollection>;
using PicoHORecHitTableProducer = PicoHcalRecHitTableProducerT<HORecHitCollection>;
using PicoHFRecHitTableProducer = PicoHcalRecHitTableProducerT<HFRecHitCollection>;

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoEcalRecHitTableProducer);
DEFINE_FWK_MODULE(PicoHBHERecHitTableProducer);
DEFINE_FWK_MODULE(PicoHORecHitTableProducer);
DEFINE_FWK_MODULE(PicoHFRecHitTableProducer);
