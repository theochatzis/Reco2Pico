#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/Framework/interface/MakerMacros.h"

#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "FWCore/Utilities/interface/Exception.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/NanoAOD/interface/MergeableCounterTable.h"

#include "SimDataFormats/GeneratorProducts/interface/GenEventInfoProduct.h"
#include "SimDataFormats/PileupSummaryInfo/interface/PileupSummaryInfo.h"

#include <algorithm>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "DataFormats/Math/interface/libminifloat.h"
#include <iostream>

namespace {

struct Counter {
  long long genEventCount = 0;
  long double genEventSumw = 0.0L;
  long double genEventSumw2 = 0.0L;

  // ROOT-like bin numbering:
  //   [0]          = underflow
  //   [1..nBins]   = regular bins
  //   [nBins + 1]  = overflow
  std::vector<long double> pileupSumw;

  explicit Counter(std::size_t nPileupStorageBins = 0)
      : pileupSumw(nPileupStorageBins, 0.0L) {}

  void clear() {
    genEventCount = 0;
    genEventSumw = 0.0L;
    genEventSumw2 = 0.0L;
    std::fill(pileupSumw.begin(), pileupSumw.end(), 0.0L);
  }

  void addEvent(double weight) {
    ++genEventCount;
    genEventSumw += weight;
    genEventSumw2 += weight * weight;
  }

  void addPileup(std::size_t storageBin, double weight) {
    pileupSumw.at(storageBin) += weight;
  }

  void merge(const Counter& other) {
    if (pileupSumw.size() != other.pileupSumw.size()) {
      throw cms::Exception("LogicError")
          << "Cannot merge Pico MC bookkeeping counters with different "
          << "pileup vector sizes: "
          << pileupSumw.size() << " vs " << other.pileupSumw.size();
    }

    genEventCount += other.genEventCount;
    genEventSumw += other.genEventSumw;
    genEventSumw2 += other.genEventSumw2;

    for (std::size_t i = 0; i < pileupSumw.size(); ++i) {
      pileupSumw[i] += other.pileupSumw[i];
    }
  }
};

}  // namespace


class PicoMCBookkeepingProducer
    : public edm::global::EDProducer<
          edm::StreamCache<Counter>,
          edm::RunSummaryCache<Counter>,
          edm::EndRunProducer> {

public:
  explicit PicoMCBookkeepingProducer(const edm::ParameterSet& config)
      : genInfoToken_(
            consumes<GenEventInfoProduct>(
                config.getParameter<edm::InputTag>("genInfo"))),
        pileupEdges_(
            config.getParameter<std::vector<double>>("pileupEdges")),
        requirePileup_(
            config.getParameter<bool>("requirePileup")) {

    if (pileupEdges_.size() < 2) {
      throw cms::Exception("Configuration")
          << "PicoMCBookkeepingProducer requires at least two pileupEdges.";
    }

    if (!std::is_sorted(pileupEdges_.begin(), pileupEdges_.end()) ||
        std::adjacent_find(
            pileupEdges_.begin(),
            pileupEdges_.end(),
            std::greater_equal<double>()) != pileupEdges_.end()) {
      throw cms::Exception("Configuration")
          << "pileupEdges must be strictly increasing.";
    }
    
    const auto pileupTags =
        config.getParameter<std::vector<edm::InputTag>>("pileupInfo");

    pileupInfoTokens_.reserve(pileupTags.size());
    pileupInfoLabels_.reserve(pileupTags.size());

    for (const auto& tag : pileupTags) {
      pileupInfoTokens_.push_back(
          mayConsume<std::vector<PileupSummaryInfo>>(tag));
      pileupInfoLabels_.push_back(tag.encode());
    }

    // Event-level branch "genWeight", following the standard NanoAOD
    // GenWeightsTableProducer convention.
    produces<nanoaod::FlatTable>();

    // Run-level additive bookkeeping.
    produces<nanoaod::MergeableCounterTable, edm::Transition::EndRun>();
  }


  std::unique_ptr<Counter> beginStream(edm::StreamID) const override {
    return std::make_unique<Counter>(nPileupStorageBins());
  }


  void streamBeginRun(
      edm::StreamID id,
      const edm::Run&,
      const edm::EventSetup&) const override {

    streamCache(id)->clear();
  }


  std::shared_ptr<Counter> globalBeginRunSummary(
      const edm::Run&,
      const edm::EventSetup&) const override {

    return std::make_shared<Counter>(nPileupStorageBins());
  }


  void streamEndRunSummary(
      edm::StreamID id,
      const edm::Run&,
      const edm::EventSetup&,
      Counter* runCounter) const override {

    runCounter->merge(*streamCache(id));
  }


  void globalEndRunSummary(
      const edm::Run&,
      const edm::EventSetup&,
      Counter*) const override {}


  void produce(
      edm::StreamID id,
      edm::Event& event,
      const edm::EventSetup&) const override {

    const auto genInfo = event.getHandle(genInfoToken_);

    if (!genInfo.isValid()) {
      throw cms::Exception("ProductNotFound")
          << "PicoMCBookkeepingProducer could not read GenEventInfoProduct "
          << "from 'generator'. This module should only be scheduled for MC.";
    }

    const double genWeight = genInfo->weight();
    
    // ------------------------------------------------------------
    // Event-level genWeight
    // ------------------------------------------------------------
    auto genWeightTable =
        std::make_unique<nanoaod::FlatTable>(
            1,
            "genWeight",
            true);

    genWeightTable->setDoc("generator weight");
    genWeightTable->addColumnValue<float>(
        "",
        static_cast<float>(genWeight),
        "generator weight");

    event.put(std::move(genWeightTable));

    // ------------------------------------------------------------
    // Additive sample bookkeeping
    // ------------------------------------------------------------
    const int pileupMantissaBits_ = 10;

    Counter* counter = streamCache(id);
    counter->addEvent(genWeight);

    bool foundPileupCollection = false;
    bool foundBX0 = false;

    for (const auto& token : pileupInfoTokens_) {
      const auto pileupInfo = event.getHandle(token);

      if (!pileupInfo.isValid()) {
        continue;
      }

      foundPileupCollection = true;

      for (const auto& pu : *pileupInfo) {
        if (pu.getBunchCrossing() != 0) {
          continue;
        }

        // const double nTrueInt = pu.getTrueNumInteractions();
        // counter->addPileup(
        //     pileupStorageBin(nTrueInt),
        //     genWeight);
        float nTrueInt = pu.getTrueNumInteractions();
        
        // Match NanoAOD Pileup_nTrueInt precision.
        // NPUTablesProducer stores nTrueInt with 10 mantissa bits.
        nTrueInt = MiniFloatConverter::reduceMantissaToNbitsRounding(nTrueInt, pileupMantissaBits_);
        
        counter->addPileup(
            pileupStorageBin(nTrueInt),
            genWeight
        );

        foundBX0 = true;
        break;
      }

      // A valid collection was found; do not try fallback labels.
      break;
    }

    if (requirePileup_ && !foundPileupCollection) {
      std::string labels;

      for (std::size_t i = 0; i < pileupInfoLabels_.size(); ++i) {
        if (i != 0) {
          labels += ", ";
        }
        labels += pileupInfoLabels_[i];
      }

      throw cms::Exception("ProductNotFound")
          << "PicoMCBookkeepingProducer could not find pileup information. "
          << "Tried: " << labels
          << ". Set requirePileup=False for samples that genuinely have "
          << "no pileup information.";
    }

    if (requirePileup_ && foundPileupCollection && !foundBX0) {
      throw cms::Exception("MissingPileupBX0")
          << "PileupSummaryInfo was found, but no bunch-crossing-0 entry "
          << "was present.";
    }
  }


  void globalEndRunProduce(
      edm::Run& run,
      const edm::EventSetup&,
      const Counter* counter) const override {

    auto table =
        std::make_unique<nanoaod::MergeableCounterTable>();

    table->addInt(
        "genEventCount",
        "Number of generator events processed before the Pico skim",
        counter->genEventCount);

    table->addFloat(
        "genEventSumw",
        "Sum of generator event weights before the Pico skim",
        static_cast<double>(counter->genEventSumw));

    table->addFloat(
        "genEventSumw2",
        "Sum of squared generator event weights before the Pico skim",
        static_cast<double>(counter->genEventSumw2));

    std::vector<double> pileupSumw;
    pileupSumw.reserve(counter->pileupSumw.size());

    for (const auto value : counter->pileupSumw) {
      pileupSumw.push_back(static_cast<double>(value));
    }

    table->addVFloat(
        "pileupSumw",
        "Generator-weighted true-pileup bin contents. "
        "Includes underflow at index 0 and overflow at the final index; "
        "bin edges are stored in nanoMetadata.bookkeepingSchema.",
        pileupSumw);

    run.put(std::move(table));
  }


  static void fillDescriptions(
      edm::ConfigurationDescriptions& descriptions) {

    edm::ParameterSetDescription desc;

    desc.add<edm::InputTag>(
        "genInfo",
        edm::InputTag("generator"));

    desc.add<std::vector<edm::InputTag>>(
        "pileupInfo",
        std::vector<edm::InputTag>{
            edm::InputTag("slimmedAddPileupInfo"),
            edm::InputTag("addPileupInfo"),
        });

    desc.add<std::vector<double>>(
        "pileupEdges",
        defaultPileupEdges());

    desc.add<bool>(
        "requirePileup",
        true);

    descriptions.add(
        "picoMCBookkeepingProducer",
        desc);
  }


private:
  static std::vector<double> defaultPileupEdges() {
    std::vector<double> edges;
    edges.reserve(101);

    for (int i = 0; i <= 100; ++i) {
      edges.push_back(static_cast<double>(i));
    }

    return edges;
  }


  std::size_t nPileupStorageBins() const {
    // Number of regular bins = edges - 1.
    // Add ROOT-style underflow and overflow.
    return (pileupEdges_.size() - 1) + 2;
  }


  std::size_t pileupStorageBin(double value) const {
    const std::size_t nRegularBins =
        pileupEdges_.size() - 1;

    if (value < pileupEdges_.front()) {
      return 0;
    }

    if (value >= pileupEdges_.back()) {
      return nRegularBins + 1;
    }

    // For value in [edge_i, edge_{i+1}), return ROOT-like bin i+1.
    const auto upper =
        std::upper_bound(
            pileupEdges_.begin(),
            pileupEdges_.end(),
            value);

    return static_cast<std::size_t>(
        std::distance(pileupEdges_.begin(), upper));
  }


  const edm::EDGetTokenT<GenEventInfoProduct>
      genInfoToken_;

  std::vector<
      edm::EDGetTokenT<std::vector<PileupSummaryInfo>>
  > pileupInfoTokens_;

  std::vector<std::string>
      pileupInfoLabels_;

  const std::vector<double>
      pileupEdges_;

  const bool
      requirePileup_;
};


DEFINE_FWK_MODULE(PicoMCBookkeepingProducer);
