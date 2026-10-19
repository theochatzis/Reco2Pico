#ifndef Reco2Pico_PicoProducer_PicoCaloSimHits_h
#define Reco2Pico_PicoProducer_PicoCaloSimHits_h
// Calorimeter sim hits (PCaloHit) of the signal event summed per cell and
// per Geant4 particle, in the GeV-equivalent scale of the digitiser:
// HCAL hits are relabelled from the Geant4 test numbering to HcalDetId and
// scaled with the digitiser sampling factors; HF photoelectrons with the HF
// factors. Shared by PicoSimCaloCandidateProducer (per-particle deposits)
// and PicoPFCandTruthProducer (attribution of reconstructed clusters).
#include <cstdint>
#include <map>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/ConsumesCollector.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/Utilities/interface/ESGetToken.h"

#include "DataFormats/DetId/interface/DetId.h"
#include "DataFormats/HcalDetId/interface/HcalDetId.h"
#include "Geometry/HcalCommonData/interface/HcalDDDRecConstants.h"
#include "Geometry/HcalCommonData/interface/HcalHitRelabeller.h"
#include "Geometry/Records/interface/HcalRecNumberingRecord.h"
#include "SimDataFormats/CaloHit/interface/PCaloHitContainer.h"

namespace pico {

  enum CaloSub { ECAL = 0, ES = 1, HCAL = 2, HO = 3, HF = 4, NSUB = 5 };

  struct CellShares {
    double total = 0;
    std::map<int, double> perTrack;  // SimTrack index -> GeV-equivalent deposit
  };

  class CaloSimHits {
  public:
    CaloSimHits(const edm::ParameterSet& cfg, edm::ConsumesCollector&& cc)
        : hcalRecToken_(cc.esConsumes<HcalDDDRecConstants, HcalRecNumberingRecord>()),
          hcalTestNumbering_(cfg.getParameter<bool>("hcalTestNumbering")),
          hbFactors_(cfg.getParameter<std::vector<double>>("hbSamplingFactors")),
          heFactors_(cfg.getParameter<std::vector<double>>("heSamplingFactors")),
          hoFactors_(cfg.getParameter<std::vector<double>>("hoSamplingFactors")),
          hf1Factor_(cfg.getParameter<double>("hf1SamplingFactor")),
          hf2Factor_(cfg.getParameter<double>("hf2SamplingFactor")),
          heFirstRing_(cfg.getParameter<int>("heFirstRing")),
          relabeller_(false) {
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("ecalHits"))
        ecalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("preshowerHits"))
        esTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("hcalHits"))
        hcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
    }

    static void fillDescription(edm::ParameterSetDescription& desc) {
      desc.add<std::vector<edm::InputTag>>("ecalHits", {edm::InputTag("g4SimHits", "EcalHitsEB"), edm::InputTag("g4SimHits", "EcalHitsEE")});
      desc.add<std::vector<edm::InputTag>>("preshowerHits", {edm::InputTag("g4SimHits", "EcalHitsES")});
      desc.add<std::vector<edm::InputTag>>("hcalHits", {edm::InputTag("g4SimHits", "HcalHits")});
      desc.add<bool>("hcalTestNumbering", true);
      desc.add<std::vector<double>>("hbSamplingFactors", {});
      desc.add<std::vector<double>>("heSamplingFactors", {});
      desc.add<std::vector<double>>("hoSamplingFactors", {});
      desc.add<double>("hf1SamplingFactor", 1.0);
      desc.add<double>("hf2SamplingFactor", 1.0);
      desc.add<int>("heFirstRing", 16);
    }

    double hcalFactor(const HcalDetId& id) const {
      const int ieta = id.ietaAbs();
      switch (id.subdet()) {
        case HcalBarrel:
          return (ieta >= 1 && size_t(ieta) <= hbFactors_.size()) ? hbFactors_[ieta - 1] : 1.0;
        case HcalEndcap: {
          const int k = ieta - heFirstRing_;
          return (k >= 0 && size_t(k) < heFactors_.size()) ? heFactors_[k] : 1.0;
        }
        case HcalOuter:
          return (ieta >= 1 && size_t(ieta) <= hoFactors_.size()) ? hoFactors_[ieta - 1] : 1.0;
        case HcalForward:
          return id.depth() == 1 ? hf1Factor_ : hf2Factor_;
        default:
          return 1.0;
      }
    }

    // cells[sub][rawId] -> shares; rowOfTrackId maps Geant4 ids to SimTrack indices
    void build(const edm::Event& event,
               const edm::EventSetup& setup,
               const std::unordered_map<unsigned int, int>& rowOfTrackId,
               std::map<uint32_t, CellShares> cells[NSUB]) const {
      auto addHit = [&](CaloSub sub, uint32_t rawId, int trackId, double energy) {
        auto it = rowOfTrackId.find(static_cast<unsigned int>(trackId));
        if (it == rowOfTrackId.end() || energy <= 0)
          return;
        CellShares& c = cells[sub][rawId];
        c.total += energy;
        c.perTrack[it->second] += energy;
      };
      for (const auto& tok : ecalTokens_)
        for (const auto& h : event.get(tok))
          addHit(ECAL, h.id(), h.geantTrackId(), h.energy());
      for (const auto& tok : esTokens_)
        for (const auto& h : event.get(tok))
          addHit(ES, h.id(), h.geantTrackId(), h.energy());
      if (hcalTokens_.empty())
        return;
      std::vector<PCaloHit> hits;
      for (const auto& tok : hcalTokens_) {
        const auto& c = event.get(tok);
        hits.insert(hits.end(), c.begin(), c.end());
      }
      if (hcalTestNumbering_) {
        const HcalDDDRecConstants* rec = &setup.getData(hcalRecToken_);
        relabeller_.setGeometry(rec);
        relabeller_.process(hits);
      }
      for (const auto& h : hits) {
        const HcalDetId id(h.id());
        if (id.det() != DetId::Hcal)
          continue;
        CaloSub sub = HCAL;
        if (id.subdet() == HcalOuter)
          sub = HO;
        else if (id.subdet() == HcalForward)
          sub = HF;
        else if (id.subdet() != HcalBarrel && id.subdet() != HcalEndcap)
          continue;
        addHit(sub, id.rawId(), h.geantTrackId(), h.energy() * hcalFactor(id));
      }
    }

  private:
    std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>> ecalTokens_, esTokens_, hcalTokens_;
    edm::ESGetToken<HcalDDDRecConstants, HcalRecNumberingRecord> hcalRecToken_;
    bool hcalTestNumbering_;
    std::vector<double> hbFactors_, heFactors_, hoFactors_;
    double hf1Factor_, hf2Factor_;
    int heFirstRing_;
    mutable HcalHitRelabeller relabeller_;
  };

}  // namespace pico

#endif
