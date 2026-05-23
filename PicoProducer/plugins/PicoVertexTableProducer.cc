#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "CommonTools/Utils/interface/StringCutObjectSelector.h"

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
#include "DataFormats/VertexReco/interface/Vertex.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/Utilities/interface/InputTag.h"


class PicoVertexTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoVertexTableProducer(const edm::ParameterSet& params);
  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

private:
  void produce(edm::Event& event, const edm::EventSetup&) override;

  bool keep(const std::string& name) const {
    return variables_.empty() || variables_.count(name);
  }

  std::string doc(const std::string& name, const std::string& fallback) const {
    if (!variablesPSet_.existsAs<edm::ParameterSet>(name)) return fallback;
    const auto& p = variablesPSet_.getParameter<edm::ParameterSet>(name);
    if (p.existsAs<std::string>("doc")) return p.getParameter<std::string>("doc");
    return fallback;
  }

  int precision(const std::string& name, int fallback) const {
    if (!variablesPSet_.existsAs<edm::ParameterSet>(name)) return fallback;
    const auto& p = variablesPSet_.getParameter<edm::ParameterSet>(name);
    if (p.existsAs<int>("precision")) return p.getParameter<int>("precision");
    return fallback;
  }

  const edm::EDGetTokenT<std::vector<reco::Vertex>> pvs_;
  const edm::EDGetTokenT<pat::PackedCandidateCollection> pfc_;
  const edm::EDGetTokenT<edm::ValueMap<float>> pvsScore_;

  const StringCutObjectSelector<reco::Vertex> goodPvCut_;
  const std::string goodPvCutString_;
  const std::string pvName_;

  const edm::ParameterSet variablesPSet_;
  std::set<std::string> variables_;
};


PicoVertexTableProducer::PicoVertexTableProducer(const edm::ParameterSet& params)
    : pvs_(consumes<std::vector<reco::Vertex>>(params.getParameter<edm::InputTag>("pvSrc"))),
      pfc_(consumes<pat::PackedCandidateCollection>(params.getParameter<edm::InputTag>("pfcSrc"))),
      pvsScore_(consumes<edm::ValueMap<float>>(params.getParameter<edm::InputTag>("pvSrc"))),
      goodPvCut_(params.getParameter<std::string>("goodPvCut"), true),
      goodPvCutString_(params.getParameter<std::string>("goodPvCut")),
      pvName_(params.getParameter<std::string>("pvName")),
      variablesPSet_(params.getParameter<edm::ParameterSet>("variables")) {
  for (const auto& name : variablesPSet_.getParameterNamesForType<edm::ParameterSet>()) {
    variables_.insert(name);
  }

  produces<nanoaod::FlatTable>("pv");
}


void PicoVertexTableProducer::produce(edm::Event& event, const edm::EventSetup&) {
  auto pvsIn = event.getHandle(pvs_);
  auto pfcIn = event.getHandle(pfc_);

  const edm::ValueMap<float>* pvsScoreProd = nullptr;
  edm::Handle<edm::ValueMap<float>> pvsScoreHandle;
  if (event.getByToken(pvsScore_, pvsScoreHandle)) {
    pvsScoreProd = pvsScoreHandle.product();
  }

  auto pvTable = std::make_unique<nanoaod::FlatTable>(1, pvName_, true);

  if (!pvsIn.isValid() || pvsIn->empty()) {
    if (keep("ndof")) {
      pvTable->addColumnValue<float>("ndof", 0.0, doc("ndof", "main primary vertex number of degree of freedom"), precision("ndof", 8));
    }
    if (keep("x")) {
      pvTable->addColumnValue<float>("x", 0.0, doc("x", "main primary vertex position x coordinate"), precision("x", 10));
    }
    if (keep("y")) {
      pvTable->addColumnValue<float>("y", 0.0, doc("y", "main primary vertex position y coordinate"), precision("y", 10));
    }
    if (keep("z")) {
      pvTable->addColumnValue<float>("z", 0.0, doc("z", "main primary vertex position z coordinate"), precision("z", 16));
    }
    if (keep("chi2")) {
      pvTable->addColumnValue<float>("chi2", 0.0, doc("chi2", "main primary vertex reduced chi2"), precision("chi2", 8));
    }
    if (keep("npvs")) {
      pvTable->addColumnValue<uint8_t>("npvs", 0, doc("npvs", "total number of reconstructed primary vertices"));
    }
    if (keep("npvsGood")) {
      pvTable->addColumnValue<uint8_t>("npvsGood", 0, doc("npvsGood", "number of good reconstructed primary vertices. selection:" + goodPvCutString_));
    }
    if (keep("score")) {
      pvTable->addColumnValue<float>("score", 0.0, doc("score", "main primary vertex score, i.e. sum pt2 of clustered objects"), precision("score", 8));
    }
    if (keep("sumpt2")) {
      pvTable->addColumnValue<float>("sumpt2", 0.0, doc("sumpt2", "sum pt2 of pf charged candidates for the main primary vertex"), precision("sumpt2", 10));
    }
    if (keep("sumpx")) {
      pvTable->addColumnValue<float>("sumpx", 0.0, doc("sumpx", "sum px of pf charged candidates for the main primary vertex"), precision("sumpx", 10));
    }
    if (keep("sumpy")) {
      pvTable->addColumnValue<float>("sumpy", 0.0, doc("sumpy", "sum py of pf charged candidates for the main primary vertex"), precision("sumpy", 10));
    }

    event.put(std::move(pvTable), "pv");
    return;
  }

  const auto& pv0 = (*pvsIn)[0];

  int goodPVs = 0;
  for (const auto& pv : *pvsIn) {
    if (goodPvCut_(pv)) ++goodPVs;
  }

  float pv_sumpt2 = 0.0;
  float pv_sumpx = 0.0;
  float pv_sumpy = 0.0;

  if (pfcIn.isValid()) {
    for (const auto& obj : *pfcIn) {
      if (obj.charge() == 0) continue;

      double dz = std::abs(obj.dz(pv0.position()));
      bool include_pfc = false;

      if (dz < 0.2) {
        include_pfc = true;

        for (size_t j = 1; j < pvsIn->size(); ++j) {
          const double newdz = std::abs(obj.dz((*pvsIn)[j].position()));
          if (newdz < dz) {
            include_pfc = false;
            break;
          }
        }
      }

      if (include_pfc) {
        const float pt = obj.pt();
        pv_sumpt2 += pt * pt;
        pv_sumpx += obj.px();
        pv_sumpy += obj.py();
      }
    }
  }

  if (keep("ndof")) {
    pvTable->addColumnValue<float>("ndof", pv0.ndof(), doc("ndof", "main primary vertex number of degree of freedom"), precision("ndof", 8));
  }
  if (keep("x")) {
    pvTable->addColumnValue<float>("x", pv0.position().x(), doc("x", "main primary vertex position x coordinate"), precision("x", 10));
  }
  if (keep("y")) {
    pvTable->addColumnValue<float>("y", pv0.position().y(), doc("y", "main primary vertex position y coordinate"), precision("y", 10));
  }
  if (keep("z")) {
    pvTable->addColumnValue<float>("z", pv0.position().z(), doc("z", "main primary vertex position z coordinate"), precision("z", 16));
  }
  if (keep("chi2")) {
    pvTable->addColumnValue<float>("chi2", pv0.normalizedChi2(), doc("chi2", "main primary vertex reduced chi2"), precision("chi2", 8));
  }
  if (keep("npvs")) {
    pvTable->addColumnValue<uint8_t>(
        "npvs",
        static_cast<uint8_t>(std::min<size_t>(pvsIn->size(), 255)),
        doc("npvs", "total number of reconstructed primary vertices"));
  }
  if (keep("npvsGood")) {
    pvTable->addColumnValue<uint8_t>(
        "npvsGood",
        static_cast<uint8_t>(std::min(goodPVs, 255)),
        doc("npvsGood", "number of good reconstructed primary vertices. selection:" + goodPvCutString_));
  }
  if (keep("score")) {
    float score = 0.0;
    if (pvsScoreProd) {
      score = pvsScoreProd->get(pvsIn.id(), 0);
    } else {
      score = pv_sumpt2;
    }

    pvTable->addColumnValue<float>(
        "score",
        score,
        doc("score", "main primary vertex score, i.e. sum pt2 of clustered objects"),
        precision("score", 8));
  }
  if (keep("sumpt2")) {
    pvTable->addColumnValue<float>(
        "sumpt2",
        pv_sumpt2,
        doc("sumpt2", "sum pt2 of pf charged candidates for the main primary vertex"),
        precision("sumpt2", 10));
  }
  if (keep("sumpx")) {
    pvTable->addColumnValue<float>(
        "sumpx",
        pv_sumpx,
        doc("sumpx", "sum px of pf charged candidates for the main primary vertex"),
        precision("sumpx", 10));
  }
  if (keep("sumpy")) {
    pvTable->addColumnValue<float>(
        "sumpy",
        pv_sumpy,
        doc("sumpy", "sum py of pf charged candidates for the main primary vertex"),
        precision("sumpy", 10));
  }

  event.put(std::move(pvTable), "pv");
}


void PicoVertexTableProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("pvSrc")->setComment("std::vector<reco::Vertex> primary vertex input collection");
  desc.add<edm::InputTag>("pfcSrc")->setComment("packedPFCandidates input collection");
  desc.add<std::string>("goodPvCut")->setComment("selection on the primary vertex");
  desc.add<std::string>("pvName", "PV")->setComment("name of the flat table output");

  edm::ParameterSetDescription vars;
  vars.setAllowAnything();
  desc.add<edm::ParameterSetDescription>("variables", vars);

  descriptions.addWithDefaultLabel(desc);
}


DEFINE_FWK_MODULE(PicoVertexTableProducer);