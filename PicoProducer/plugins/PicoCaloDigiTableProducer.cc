// Flat tables of the ECAL and HCAL digis: the ADC samples of every cell above an amplitude
// threshold, with each sample also on the rechit energy scale (pedestal subtracted, gain
// and calibration applied as the reconstruction does), so that the pulse the fit saw can be
// drawn next to the rechit and the simulated deposits per crossing.
//
//   PicoEcalDigiTableProducer   EBDigiCollection / EEDigiCollection (10 samples; MGPA gain id)
//       e<i>   = (adc - pedestal[gain]) x gain ratio to gain 12 x ADCToGeV x intercalibration
//                x laser correction (as the rechit energy)
//   PicoHcalDigiTableProducer   QIE11DigiCollection (HB and HE, 8 or 10 samples, TDC)
//       fc<i>  = charge of the ADC code (QIE coder), e<i> = (fc - pedestal[capid]) x gain
//
// A digi is kept when the largest e<i> exceeds minAmplitude (GeV).
#include <algorithm>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/ESHandle.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/ESGetToken.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/EcalDigi/interface/EcalDigiCollections.h"
#include "DataFormats/EcalDetId/interface/EBDetId.h"
#include "DataFormats/EcalDetId/interface/EEDetId.h"
#include "DataFormats/HcalDigi/interface/HcalDigiCollections.h"
#include "DataFormats/HcalDigi/interface/QIE11DataFrame.h"
#include "DataFormats/HcalDetId/interface/HcalDetId.h"

#include "CondFormats/EcalObjects/interface/EcalPedestals.h"
#include "CondFormats/DataRecord/interface/EcalPedestalsRcd.h"
#include "CondFormats/EcalObjects/interface/EcalGainRatios.h"
#include "CondFormats/DataRecord/interface/EcalGainRatiosRcd.h"
#include "CondFormats/EcalObjects/interface/EcalADCToGeVConstant.h"
#include "CondFormats/DataRecord/interface/EcalADCToGeVConstantRcd.h"
#include "CondFormats/EcalObjects/interface/EcalIntercalibConstants.h"
#include "CondFormats/DataRecord/interface/EcalIntercalibConstantsRcd.h"
#include "CalibCalorimetry/EcalLaserCorrection/interface/EcalLaserDbService.h"
#include "CalibCalorimetry/EcalLaserCorrection/interface/EcalLaserDbRecord.h"
#include "CalibFormats/HcalObjects/interface/HcalDbService.h"
#include "CalibFormats/HcalObjects/interface/HcalDbRecord.h"
#include "CalibFormats/HcalObjects/interface/HcalCalibrations.h"
#include "CondFormats/HcalObjects/interface/HcalQIECoder.h"
#include "CondFormats/HcalObjects/interface/HcalQIEShape.h"

namespace {
  template <typename T>
  void addIndexed(nanoaod::FlatTable& table, const std::string& prefix, const std::vector<std::vector<T>>& cols,
                  const std::string& doc, int precision = -1) {
    for (size_t i = 0; i < cols.size(); ++i)
      table.addColumn<T>(prefix + std::to_string(i), cols[i], doc + " of sample " + std::to_string(i), precision);
  }
}  // namespace

template <typename Collection>
class PicoEcalDigiTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoEcalDigiTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<Collection>(cfg.getParameter<edm::InputTag>("src"))),
        pedToken_(esConsumes()),
        gainToken_(esConsumes()),
        adcToGeVToken_(esConsumes()),
        icalToken_(esConsumes()),
        laserToken_(esConsumes()),
        name_(cfg.getParameter<std::string>("name")),
        minAmplitude_(cfg.getParameter<double>("minAmplitude")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& digis = event.get(srcToken_);
    const auto& peds = setup.getData(pedToken_);
    const auto& gains = setup.getData(gainToken_);
    const auto& adcToGeV = setup.getData(adcToGeVToken_);
    const auto& ical = setup.getData(icalToken_);
    const auto& laser = setup.getData(laserToken_);
    constexpr int kSamples = 10;

    std::vector<uint32_t> rawId;
    std::vector<int32_t> ieta, iphi, ix, iy, zside, saturated;
    std::vector<std::vector<int32_t>> adc(kSamples), gain(kSamples);
    std::vector<std::vector<float>> e(kSamples);
    std::vector<float> ped12, gevPerAdc, laserCorr;

    for (const auto& digi : digis) {
      const typename Collection::Digi frame(digi);
      const DetId id = frame.id();
      const bool barrel = id.subdetId() == EcalBarrel;
      const auto ped = peds.find(id.rawId());
      const auto gr = gains.find(id.rawId());
      const auto ic = ical.find(id.rawId());
      if (ped == peds.end() || gr == gains.end() || ic == ical.end())
        continue;
      const float lc = laser.getLaserCorrection(id, event.time());
      const float toGeV = (barrel ? adcToGeV.getEBValue() : adcToGeV.getEEValue()) * (*ic) * lc;
      const float g12over6 = gr->gain12Over6(), g6over1 = gr->gain6Over1();
      std::vector<int32_t> a(kSamples, 0), g(kSamples, 0);
      std::vector<float> en(kSamples, 0.f);
      int sat = 0;
      float emax = -1.f;
      for (int i = 0; i < std::min(kSamples, frame.size()); ++i) {
        const auto s = frame.sample(i);
        a[i] = s.adc();
        g[i] = s.gainId();
        float amp;  // ADC counts at gain 12
        switch (s.gainId()) {
          case 1: amp = s.adc() - ped->mean_x12; break;
          case 2: amp = (s.adc() - ped->mean_x6) * g12over6; break;
          case 3: amp = (s.adc() - ped->mean_x1) * g6over1 * g12over6; break;
          default: amp = (s.adc() - ped->mean_x1) * g6over1 * g12over6; sat = 1; break;
        }
        en[i] = amp * toGeV;
        emax = std::max(emax, en[i]);
      }
      if (emax < minAmplitude_)
        continue;
      rawId.push_back(id.rawId());
      saturated.push_back(sat);
      ped12.push_back(ped->mean_x12);
      gevPerAdc.push_back(toGeV);
      laserCorr.push_back(lc);
      int32_t oIeta = 0, oIphi = 0, oIx = 0, oIy = 0, oZ = 0;
      if (barrel) {
        const EBDetId eb(id);
        oIeta = eb.ieta();
        oIphi = eb.iphi();
      } else {
        const EEDetId ee(id);
        oIx = ee.ix();
        oIy = ee.iy();
        oZ = ee.zside();
      }
      ieta.push_back(oIeta);
      iphi.push_back(oIphi);
      ix.push_back(oIx);
      iy.push_back(oIy);
      zside.push_back(oZ);
      for (int i = 0; i < kSamples; ++i) {
        adc[i].push_back(a[i]);
        gain[i].push_back(g[i]);
        e[i].push_back(en[i]);
      }
    }

    auto table = std::make_unique<nanoaod::FlatTable>(rawId.size(), name_, false, false);
    table->addColumn<uint32_t>("rawId", rawId, "DetId raw identifier");
    table->addColumn<int32_t>("ieta", ieta, "EB ieta; 0 outside EB");
    table->addColumn<int32_t>("iphi", iphi, "EB iphi; 0 outside EB");
    table->addColumn<int32_t>("ix", ix, "EE ix; 0 outside EE");
    table->addColumn<int32_t>("iy", iy, "EE iy; 0 outside EE");
    table->addColumn<int32_t>("zside", zside, "EE z side; 0 outside EE");
    table->addColumn<int32_t>("saturated", saturated, "1 if a sample has gain id 0 (saturated)");
    table->addColumn<float>("pedestal", ped12, "pedestal at gain 12 [ADC]", 10);
    table->addColumn<float>("gevPerAdc", gevPerAdc, "GeV per ADC count at gain 12 (ADCToGeV x intercalibration x laser)", 10);
    table->addColumn<float>("laser", laserCorr, "laser (transparency) correction", 10);
    addIndexed(*table, "adc", adc, "ADC code");
    addIndexed(*table, "gain", gain, "MGPA gain id (1: x12, 2: x6, 3: x1, 0: saturated)");
    addIndexed(*table, "e", e, "pedestal-subtracted amplitude on the rechit scale [GeV]", 10);
    event.put(std::move(table));
  }

private:
  const edm::EDGetTokenT<Collection> srcToken_;
  const edm::ESGetToken<EcalPedestals, EcalPedestalsRcd> pedToken_;
  const edm::ESGetToken<EcalGainRatios, EcalGainRatiosRcd> gainToken_;
  const edm::ESGetToken<EcalADCToGeVConstant, EcalADCToGeVConstantRcd> adcToGeVToken_;
  const edm::ESGetToken<EcalIntercalibConstants, EcalIntercalibConstantsRcd> icalToken_;
  const edm::ESGetToken<EcalLaserDbService, EcalLaserDbRecord> laserToken_;
  const std::string name_;
  const double minAmplitude_;
};

class PicoHcalDigiTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoHcalDigiTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<QIE11DigiCollection>(cfg.getParameter<edm::InputTag>("src"))),
        dbToken_(esConsumes()),
        name_(cfg.getParameter<std::string>("name")),
        minAmplitude_(cfg.getParameter<double>("minAmplitude")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& digis = event.get(srcToken_);
    const HcalDbService& conditions = setup.getData(dbToken_);
    constexpr int kSamples = 10;

    std::vector<uint32_t> rawId;
    std::vector<int32_t> subdet, ieta, iphi, depth, soi, nSamples;
    std::vector<std::vector<int32_t>> adc(kSamples), tdc(kSamples), capid(kSamples);
    std::vector<std::vector<float>> fc(kSamples), e(kSamples);
    std::vector<float> pedestal0, gain0;

    for (auto it = digis.begin(); it != digis.end(); ++it) {
      const QIE11DataFrame frame(*it);
      const HcalDetId id(frame.id());
      if (id.subdet() != HcalBarrel && id.subdet() != HcalEndcap)
        continue;
      const HcalQIECoder* coder = conditions.getHcalCoder(id);
      const HcalQIEShape* shape = conditions.getHcalShape(coder);
      const HcalCalibrations& calib = conditions.getHcalCalibrations(id);
      std::vector<int32_t> a(kSamples, 0), t(kSamples, 0), c(kSamples, 0);
      std::vector<float> q(kSamples, 0.f), en(kSamples, 0.f);
      float emax = -1.f;
      for (int i = 0; i < std::min(kSamples, frame.samples()); ++i) {
        const auto s = frame[i];
        a[i] = s.adc();
        t[i] = s.tdc();
        c[i] = s.capid();
        q[i] = coder->charge(*shape, s.adc(), s.capid());
        en[i] = (q[i] - calib.pedestal(s.capid())) * calib.respcorrgain(s.capid());
        emax = std::max(emax, en[i]);
      }
      if (emax < minAmplitude_)
        continue;
      rawId.push_back(id.rawId());
      subdet.push_back(id.subdet());
      ieta.push_back(id.ieta());
      iphi.push_back(id.iphi());
      depth.push_back(id.depth());
      soi.push_back(frame.presamples());
      nSamples.push_back(std::min(kSamples, frame.samples()));
      pedestal0.push_back(calib.pedestal(0));
      gain0.push_back(calib.respcorrgain(0));
      for (int i = 0; i < kSamples; ++i) {
        adc[i].push_back(a[i]);
        tdc[i].push_back(t[i]);
        capid[i].push_back(c[i]);
        fc[i].push_back(q[i]);
        e[i].push_back(en[i]);
      }
    }

    auto table = std::make_unique<nanoaod::FlatTable>(rawId.size(), name_, false, false);
    table->addColumn<uint32_t>("rawId", rawId, "DetId raw identifier");
    table->addColumn<int32_t>("subdet", subdet, "HCAL subdetector enum value (1 HB, 2 HE)");
    table->addColumn<int32_t>("ieta", ieta, "HCAL ieta");
    table->addColumn<int32_t>("iphi", iphi, "HCAL iphi");
    table->addColumn<int32_t>("depth", depth, "HCAL depth");
    table->addColumn<int32_t>("soi", soi, "sample of interest (the in-time bunch crossing)");
    table->addColumn<int32_t>("nSamples", nSamples, "number of samples of the digi (8 or 10; later columns are 0)");
    table->addColumn<float>("pedestal", pedestal0, "pedestal of capacitor 0 [fC]", 10);
    table->addColumn<float>("gain", gain0, "response-corrected gain of capacitor 0 [GeV/fC]", 10);
    addIndexed(*table, "adc", adc, "ADC code");
    addIndexed(*table, "tdc", tdc, "TDC code");
    addIndexed(*table, "capid", capid, "capacitor id");
    addIndexed(*table, "fc", fc, "charge [fC]", 10);
    addIndexed(*table, "e", e, "pedestal-subtracted charge on the rechit scale [GeV]", 10);
    event.put(std::move(table));
  }

private:
  const edm::EDGetTokenT<QIE11DigiCollection> srcToken_;
  const edm::ESGetToken<HcalDbService, HcalDbRecord> dbToken_;
  const std::string name_;
  const double minAmplitude_;
};

using PicoEBDigiTableProducer = PicoEcalDigiTableProducer<EBDigiCollection>;
using PicoEEDigiTableProducer = PicoEcalDigiTableProducer<EEDigiCollection>;

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoEBDigiTableProducer);
DEFINE_FWK_MODULE(PicoEEDigiTableProducer);
DEFINE_FWK_MODULE(PicoHcalDigiTableProducer);
