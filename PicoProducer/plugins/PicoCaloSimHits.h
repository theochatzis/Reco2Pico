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
#include <unordered_set>
#include <vector>

#include "FWCore/Framework/interface/ConsumesCollector.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/Utilities/interface/ESGetToken.h"

#include "DataFormats/DetId/interface/DetId.h"
#include "DataFormats/EcalDetId/interface/EcalSubdetector.h"
#include "DataFormats/HcalDetId/interface/HcalDetId.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "Geometry/HcalCommonData/interface/HcalDDDRecConstants.h"
#include "Geometry/HcalCommonData/interface/HcalHitRelabeller.h"
#include "Geometry/Records/interface/HcalRecNumberingRecord.h"
#include "SimDataFormats/CaloHit/interface/PCaloHitContainer.h"
#include "SimDataFormats/EncodedEventId/interface/EncodedEventId.h"

namespace pico {

  enum CaloSub { ECAL = 0, ES = 1, HCAL = 2, HO = 3, HF = 4, NSUB = 5 };

  struct CellShares {
    double total = 0;                  // signal deposit (GeV-equivalent)
    std::map<int, double> perTrack;    // signal SimTrack index -> deposit
    double puTotal = 0;                // in-time pile-up deposit
    std::map<int, double> perPUTrack;  // pile-up SimTrack index (pileup container) -> deposit
    std::map<int, double> puPerEvent;  // pile-up interaction (EncodedEventId.event()) -> deposit
    double oot = 0;                    // out-of-time pile-up deposit, all crossings
    std::map<int, double> ootPerBx;    // bunch crossing -> deposit
    double all() const { return total + puTotal; }  // in-time, what a rechit sees
  };

  inline uint64_t hitTrackKey(const PCaloHit& h) {
    return (static_cast<uint64_t>(h.eventId().rawId()) << 32) | static_cast<uint64_t>(h.geantTrackId());
  }

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
          rechitScale_(cfg.getParameter<std::vector<double>>("rechitScale")),
          relabeller_(false) {
      if (rechitScale_.size() != 8)
        throw cms::Exception("Configuration") << "rechitScale needs 8 values: EB EE ES HB HE HO HF1 HF2";
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("ecalHits"))
        ecalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("preshowerHits"))
        esTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
      for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("hcalHits"))
        hcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(tag));
      // optional pile-up truth (PicoMixedTruthProducer): in-time hits and out-of-time cell sums
      const std::string pu = cfg.getParameter<std::string>("pileupHits");
      usePileup_ = !pu.empty();
      if (usePileup_) {
        for (const char* n : {"EcalHitsEB", "EcalHitsEE"})
          puEcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, n)));
        puEsTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, "EcalHitsES")));
        puHcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, "HcalHits")));
        for (const char* n : {"OotEcalHitsEB", "OotEcalHitsEE"})
          ootEcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, n)));
        ootEsTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, "OotEcalHitsES")));
        ootHcalTokens_.push_back(cc.consumes<edm::PCaloHitContainer>(edm::InputTag(pu, "OotHcalHits")));
      }
    }

    bool usePileup() const { return usePileup_; }

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
      desc.add<std::string>("pileupHits", "");
      // GeV-equivalent -> rechit scale per subdetector (EB, EE, ES, HB, HE, HO, HF depth 1, HF depth 2):
      // the ratio of the reconstructed cell energy to the sim deposit, measured on the classically
      // mixed sample where every cell's deposit is known (1: the digitiser scale)
      desc.add<std::vector<double>>("rechitScale", {1, 1, 1, 1, 1, 1, 1, 1});
    }

    // rechit scale of a cell
    double rechitScale(CaloSub sub, uint32_t rawId) const {
      switch (sub) {
        case ECAL:
          return DetId(rawId).subdetId() == EcalBarrel ? rechitScale_[0] : rechitScale_[1];
        case ES:
          return rechitScale_[2];
        case HCAL:
          return HcalDetId(rawId).subdet() == HcalBarrel ? rechitScale_[3] : rechitScale_[4];
        case HO:
          return rechitScale_[5];
        case HF:
          return HcalDetId(rawId).depth() == 1 ? rechitScale_[6] : rechitScale_[7];
        default:
          return 1.0;
      }
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

    // track keys (event id, Geant4 id) referenced by any calorimeter sim hit of the signal
    // (pileup=false) or of the in-time pile-up (pileup=true); no relabelling or scaling needed
    void hitTrackKeys(const edm::Event& event, const edm::EventSetup&, std::unordered_set<uint64_t>& keys, bool pileup = false) const {
      const auto groups = pileup ? std::vector<const std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>>*>{&puEcalTokens_, &puEsTokens_, &puHcalTokens_}
                                 : std::vector<const std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>>*>{&ecalTokens_, &esTokens_, &hcalTokens_};
      for (const auto* toks : groups)
        for (const auto& tok : *toks)
          for (const auto& h : event.get(tok))
            if (h.energy() > 0)
              keys.insert(hitTrackKey(h));
    }

    // cells[sub][rawId] -> shares. rowOfTrackId maps the Geant4 ids of the signal SimTracks
    // to their indices; rowOfPUTrackKey (optional) maps trackKey(event id, Geant4 id) of the
    // pile-up SimTracks ("pileup" container of PicoMixedTruthProducer) to their indices.
    void build(const edm::Event& event,
               const edm::EventSetup& setup,
               const std::unordered_map<unsigned int, int>& rowOfTrackId,
               std::map<uint32_t, CellShares> cells[NSUB],
               const std::unordered_map<uint64_t, int>* rowOfPUTrackKey = nullptr) const {
      enum Kind { SIGNAL, PILEUP, OOT };
      auto addHit = [&](Kind kind, CaloSub sub, uint32_t rawId, const PCaloHit& h, double energy) {
        energy *= rechitScale(sub, rawId);
        if (energy <= 0)
          return;
        if (kind == SIGNAL) {
          auto it = rowOfTrackId.find(static_cast<unsigned int>(h.geantTrackId()));
          if (it == rowOfTrackId.end())
            return;
          CellShares& c = cells[sub][rawId];
          c.total += energy;
          c.perTrack[it->second] += energy;
        } else if (kind == PILEUP) {
          CellShares& c = cells[sub][rawId];
          c.puTotal += energy;
          c.puPerEvent[h.eventId().event()] += energy;
          if (rowOfPUTrackKey) {
            auto it = rowOfPUTrackKey->find(hitTrackKey(h));
            if (it != rowOfPUTrackKey->end())
              c.perPUTrack[it->second] += energy;
          }
        } else {
          CellShares& c = cells[sub][rawId];
          c.oot += energy;
          c.ootPerBx[h.eventId().bunchCrossing()] += energy;
        }
      };
      auto addEcalEs = [&](Kind kind, const std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>>& ecal,
                           const std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>>& es) {
        for (const auto& tok : ecal)
          for (const auto& h : event.get(tok))
            addHit(kind, ECAL, h.id(), h, h.energy());
        for (const auto& tok : es)
          for (const auto& h : event.get(tok))
            addHit(kind, ES, h.id(), h, h.energy());
      };
      auto addHcal = [&](Kind kind, const std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>>& toks) {
        if (toks.empty())
          return;
        std::vector<PCaloHit> hits;
        for (const auto& tok : toks) {
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
          addHit(kind, sub, id.rawId(), h, h.energy() * hcalFactor(id));
        }
      };
      addEcalEs(SIGNAL, ecalTokens_, esTokens_);
      addHcal(SIGNAL, hcalTokens_);
      if (usePileup_) {
        addEcalEs(PILEUP, puEcalTokens_, puEsTokens_);
        addHcal(PILEUP, puHcalTokens_);
        addEcalEs(OOT, ootEcalTokens_, ootEsTokens_);
        addHcal(OOT, ootHcalTokens_);
      }
    }

  private:
    std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>> ecalTokens_, esTokens_, hcalTokens_;
    std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>> puEcalTokens_, puEsTokens_, puHcalTokens_;
    std::vector<edm::EDGetTokenT<edm::PCaloHitContainer>> ootEcalTokens_, ootEsTokens_, ootHcalTokens_;
    bool usePileup_ = false;
    edm::ESGetToken<HcalDDDRecConstants, HcalRecNumberingRecord> hcalRecToken_;
    bool hcalTestNumbering_;
    std::vector<double> hbFactors_, heFactors_, hoFactors_;
    double hf1Factor_, hf2Factor_;
    int heFirstRing_;
    std::vector<double> rechitScale_;
    mutable HcalHitRelabeller relabeller_;
  };

}  // namespace pico

#endif
