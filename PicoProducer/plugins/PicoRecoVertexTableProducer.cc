#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"

class PicoRecoVertexTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoRecoVertexTableProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<reco::VertexCollection>(cfg.getParameter<edm::InputTag>("src"))),
        name_(cfg.getParameter<std::string>("name")) {
    produces<nanoaod::FlatTable>();
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    edm::Handle<reco::VertexCollection> vertices;
    event.getByToken(srcToken_, vertices);

    std::vector<float> x, y, z, xErr, yErr, zErr, chi2, ndof, normalizedChi2, sumPt2;
    std::vector<int32_t> nTracks;
    std::vector<uint8_t> isValid, isFake;

    x.reserve(vertices->size()); y.reserve(vertices->size()); z.reserve(vertices->size());
    for (const auto& vertex : *vertices) {
      x.push_back(vertex.x()); y.push_back(vertex.y()); z.push_back(vertex.z());
      xErr.push_back(vertex.xError()); yErr.push_back(vertex.yError()); zErr.push_back(vertex.zError());
      chi2.push_back(vertex.chi2()); ndof.push_back(vertex.ndof()); normalizedChi2.push_back(vertex.normalizedChi2());
      nTracks.push_back(static_cast<int32_t>(vertex.tracksSize()));
      isValid.push_back(vertex.isValid() ? 1 : 0);
      isFake.push_back(vertex.isFake() ? 1 : 0);

      float s2 = 0.f;
      for (const auto& ref : vertex.tracks()) {
        if (ref.isNonnull() && ref.isAvailable())
          s2 += vertex.trackWeight(ref) * ref->pt() * ref->pt();
      }
      sumPt2.push_back(s2);
    }

    auto table = std::make_unique<nanoaod::FlatTable>(vertices->size(), name_, false, false);
    table->setDoc("reco::Vertex table");
    table->addColumn<float>("x", x, "vertex x", 12);
    table->addColumn<float>("y", y, "vertex y", 12);
    table->addColumn<float>("z", z, "vertex z", 12);
    table->addColumn<float>("xErr", xErr, "vertex x uncertainty", 10);
    table->addColumn<float>("yErr", yErr, "vertex y uncertainty", 10);
    table->addColumn<float>("zErr", zErr, "vertex z uncertainty", 10);
    table->addColumn<float>("chi2", chi2, "vertex fit chi2", 10);
    table->addColumn<float>("ndof", ndof, "vertex fit ndof", 10);
    table->addColumn<float>("normalizedChi2", normalizedChi2, "vertex fit chi2/ndof", 10);
    table->addColumn<int32_t>("nTracks", nTracks, "number of tracks associated with vertex");
    table->addColumn<float>("sumPt2", sumPt2, "sum of vertex track weight times track pt squared", 10);
    table->addColumn<uint8_t>("isValid", isValid, "vertex validity flag");
    table->addColumn<uint8_t>("isFake", isFake, "fake-vertex flag");

    event.put(std::move(table));
  }

private:
  edm::EDGetTokenT<reco::VertexCollection> srcToken_;
  std::string name_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoRecoVertexTableProducer);
