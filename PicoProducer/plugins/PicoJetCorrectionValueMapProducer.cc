// Per-jet correction factor of a reco::JetCorrector (e.g. the GlobalTag
// L1FastJet or L1FastL2L3 chain) as an edm::ValueMap<float>, so that a
// SimpleFlatTableProducer can write it as an external variable of the jet
// table. The factor multiplies the raw jet four-momentum.
#include <memory>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/JetReco/interface/Jet.h"
#include "JetMETCorrections/JetCorrector/interface/JetCorrector.h"

class PicoJetCorrectionValueMapProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoJetCorrectionValueMapProducer(const edm::ParameterSet& cfg)
      : jetsToken_(consumes<edm::View<reco::Jet>>(cfg.getParameter<edm::InputTag>("jets"))),
        correctorToken_(consumes<reco::JetCorrector>(cfg.getParameter<edm::InputTag>("corrector"))) {
    produces<edm::ValueMap<float>>();
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("jets", edm::InputTag("picoAk4PFJetsPuppi"));
    desc.add<edm::InputTag>("corrector", edm::InputTag("ak4PFPuppiL1FastL2L3Corrector"));
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<edm::View<reco::Jet>> jets;
    event.getByToken(jetsToken_, jets);
    const reco::JetCorrector& corrector = event.get(correctorToken_);
    std::vector<float> factors;
    factors.reserve(jets->size());
    for (size_t i = 0; i < jets->size(); ++i)
      factors.push_back(corrector.correction((*jets)[i], jets->refAt(i)));
    auto out = std::make_unique<edm::ValueMap<float>>();
    edm::ValueMap<float>::Filler filler(*out);
    filler.insert(jets, factors.begin(), factors.end());
    filler.fill();
    event.put(std::move(out));
  }

private:
  edm::EDGetTokenT<edm::View<reco::Jet>> jetsToken_;
  edm::EDGetTokenT<reco::JetCorrector> correctorToken_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoJetCorrectionValueMapProducer);
