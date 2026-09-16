#include <cmath>

#include "FWCore/Framework/interface/stream/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/Candidate.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/Math/interface/deltaPhi.h"


class JetRefDeltaPhiFilter : public edm::stream::EDFilter<> {
public:
  explicit JetRefDeltaPhiFilter(const edm::ParameterSet& cfg)
      : refToken_(consumes<edm::View<reco::Candidate>>(
            cfg.getParameter<edm::InputTag>("refSrc"))),
        jetToken_(consumes<edm::View<reco::Candidate>>(
            cfg.getParameter<edm::InputTag>("jetSrc"))),
        minDeltaPhi_(cfg.getParameter<double>("minDeltaPhi")) {}

  bool filter(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<edm::View<reco::Candidate>> refCands;
    edm::Handle<edm::View<reco::Candidate>> jets;

    event.getByToken(refToken_, refCands);
    event.getByToken(jetToken_, jets);

    for (const auto& ref : *refCands) {
      for (const auto& jet : *jets) {
        const double dphi = std::abs(reco::deltaPhi(ref.phi(), jet.phi()));

        if (dphi > minDeltaPhi_) {
          return true;
        }
      }
    }

    return false;
  }

private:
  edm::EDGetTokenT<edm::View<reco::Candidate>> refToken_;
  edm::EDGetTokenT<edm::View<reco::Candidate>> jetToken_;
  double minDeltaPhi_;
};


DEFINE_FWK_MODULE(JetRefDeltaPhiFilter);
