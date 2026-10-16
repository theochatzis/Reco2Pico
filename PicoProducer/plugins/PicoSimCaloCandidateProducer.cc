// Per-particle calorimeter deposits from the Geant4 sim hits ("sim clusters")
// and an ideal particle-flow candidate list built from them.
//
// Every PCaloHit carries the Geant4 id of the particle that entered the
// calorimeter (CaloSD stores the id on the calo surface), so the deposits can
// be summed per SimTrack with no clustering at all. Cells are summed over all
// particles first and an optional per-cell threshold is applied to the cell
// total (as a rechit threshold would), then the cell energy is shared between
// the contributing particles in proportion to their deposits.
//
// HCAL hits are relabelled from the test numbering to HcalDetId (as the
// digitiser does) and converted to GeV-equivalent with the digitiser sampling
// factors; HF hits (photoelectrons) use the HF factors.
//
// Products (all parallel vectors):
//   calo        reco::GenParticleCollection  one massless candidate per SimTrack with deposits:
//                                            energy = sum of deposits, direction = energy-weighted cell direction
//   caloSimTrackIndex, caloEcal, caloEs, caloHcal, caloHo, caloHf, caloNCells
//   pf          reco::GenParticleCollection  ideal PF: for every terminal SimTrack (no stored
//                                            daughters, or daughters carrying less than
//                                            maxDaughterEnergyFraction of its energy), charged,
//                                            produced inside the tracker volume, inside the
//                                            acceptance and above chargedMinPt -> production momentum,
//                                            otherwise -> its calorimeter deposit (if any)
//   pfSimTrackIndex, pfKind (1 charged from momentum, 2 neutral from deposit,
//                            3 charged but not trackable, from deposit)
#include <cmath>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/ESHandle.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"

#include "DataFormats/DetId/interface/DetId.h"
#include "DataFormats/HcalDetId/interface/HcalDetId.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "Geometry/CaloGeometry/interface/CaloGeometry.h"
#include "Geometry/Records/interface/CaloGeometryRecord.h"
#include "SimDataFormats/CaloHit/interface/PCaloHitContainer.h"
#include "PicoCaloSimHits.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

class PicoSimCaloCandidateProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoSimCaloCandidateProducer(const edm::ParameterSet& cfg)
      : tracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        verticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        geomToken_(esConsumes<CaloGeometry, CaloGeometryRecord>()),
        simHits_(cfg, consumesCollector()),
        ecalCellThreshold_(cfg.getParameter<double>("ecalCellThreshold")),
        hcalCellThreshold_(cfg.getParameter<double>("hcalCellThreshold")),
        chargedMaxAbsEta_(cfg.getParameter<double>("chargedMaxAbsEta")),
        chargedMinPt_(cfg.getParameter<double>("chargedMinPt")),
        trackerMaxRadius_(cfg.getParameter<double>("trackerMaxRadius")),
        trackerMaxAbsZ_(cfg.getParameter<double>("trackerMaxAbsZ")),
        maxDaughterEnergyFraction_(cfg.getParameter<double>("maxDaughterEnergyFraction")),
        verbose_(cfg.getUntrackedParameter<bool>("verbose", false)) {
    produces<reco::GenParticleCollection>("calo");
    produces<std::vector<int>>("caloSimTrackIndex");
    produces<std::vector<float>>("caloEcal");
    produces<std::vector<float>>("caloEs");
    produces<std::vector<float>>("caloHcal");
    produces<std::vector<float>>("caloHo");
    produces<std::vector<float>>("caloHf");
    produces<std::vector<int>>("caloNCells");
    produces<reco::GenParticleCollection>("pf");
    produces<std::vector<int>>("pfSimTrackIndex");
    produces<std::vector<int>>("pfKind");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    pico::CaloSimHits::fillDescription(desc);
    desc.add<double>("ecalCellThreshold", 0.0);
    desc.add<double>("hcalCellThreshold", 0.0);
    desc.add<double>("chargedMaxAbsEta", 2.5);
    desc.add<double>("chargedMinPt", 0.5);
    desc.add<double>("trackerMaxRadius", 110.0);
    desc.add<double>("trackerMaxAbsZ", 280.0);
    desc.add<double>("maxDaughterEnergyFraction", 0.5);
    desc.addUntracked<bool>("verbose", false);
    descriptions.addWithDefaultLabel(desc);
  }

  using Sub = pico::CaloSub;
  static constexpr int NSUB = pico::NSUB;
  static constexpr Sub ECAL = pico::ECAL, ES = pico::ES, HCAL = pico::HCAL, HO = pico::HO, HF = pico::HF;

  struct Deposit {
    double e[NSUB] = {0, 0, 0, 0, 0};
    double dx = 0, dy = 0, dz = 0;  // energy-weighted unit-vector sum
    int nCells = 0;
    double total() const { return e[ECAL] + e[ES] + e[HCAL] + e[HO] + e[HF]; }
  };

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& vertices = event.get(verticesToken_);
    const CaloGeometry& geom = setup.getData(geomToken_);
    std::unordered_map<unsigned int, int> rowOfTrackId;
    for (size_t i = 0; i < tracks.size(); ++i)
      rowOfTrackId.emplace(tracks[i].trackId(), static_cast<int>(i));

    // ---- cells: sum over particles, keep per-particle shares ---------------------
    std::map<uint32_t, pico::CellShares> cells[NSUB];
    simHits_.build(event, setup, rowOfTrackId, cells);
    if (verbose_) {
      for (int sub = 0; sub < NSUB; ++sub) {
        double tot = 0;
        for (const auto& kv : cells[sub])
          tot += kv.second.total;
        edm::LogPrint("PicoSimCalo") << "sub " << sub << " cells " << cells[sub].size() << " GeV-equivalent " << tot;
      }
    }

    // ---- per-particle deposits with the cell threshold -------------------------
    std::map<int, Deposit> deposits;  // SimTrack index -> deposit
    for (int sub = 0; sub < NSUB; ++sub) {
      const double threshold = (sub == ECAL || sub == ES) ? ecalCellThreshold_ : hcalCellThreshold_;
      for (const auto& kv : cells[sub]) {
        if (kv.second.total < threshold)
          continue;
        const DetId id(kv.first);
        const auto* sdg = geom.getSubdetectorGeometry(id);
        if (!sdg) {
          if (verbose_)
            edm::LogPrint("PicoSimCalo") << "no geometry for sub " << sub << " id " << std::hex << kv.first << std::dec;
          continue;
        }
        const GlobalPoint pos = geom.getPosition(id);
        const double r = pos.mag();
        if (r <= 0)
          continue;
        for (const auto& tk : kv.second.perTrack) {
          Deposit& d = deposits[tk.first];
          d.e[sub] += tk.second;
          d.dx += tk.second * pos.x() / r;
          d.dy += tk.second * pos.y() / r;
          d.dz += tk.second * pos.z() / r;
          d.nCells += 1;
        }
      }
    }

    // ---- calo candidates -------------------------------------------------------
    auto calo = std::make_unique<reco::GenParticleCollection>();
    auto caloIdx = std::make_unique<std::vector<int>>();
    std::vector<std::unique_ptr<std::vector<float>>> caloE;
    for (int s = 0; s < NSUB; ++s)
      caloE.push_back(std::make_unique<std::vector<float>>());
    auto caloN = std::make_unique<std::vector<int>>();
    std::unordered_map<int, size_t> caloOfTrack;
    for (const auto& kv : deposits) {
      const Deposit& d = kv.second;
      const double etot = d.total();
      const double norm = std::sqrt(d.dx * d.dx + d.dy * d.dy + d.dz * d.dz);
      if (etot <= 0 || norm <= 0)
        continue;
      const SimTrack& t = tracks[kv.first];
      math::XYZTLorentzVector p4(etot * d.dx / norm, etot * d.dy / norm, etot * d.dz / norm, etot);
      caloOfTrack[kv.first] = calo->size();
      calo->emplace_back(static_cast<int>(std::lround(t.charge())), p4, math::XYZPoint(0, 0, 0), t.type(), 1, true);
      caloIdx->push_back(kv.first);
      for (int s = 0; s < NSUB; ++s)
        caloE[s]->push_back(d.e[s]);
      caloN->push_back(d.nCells);
    }

    // ---- ideal PF candidates ---------------------------------------------------
    // terminal particles: no stored daughters or daughters below maxDaughterEnergyFraction
    std::unordered_map<unsigned int, double> daughterEnergy;
    for (const auto& t : tracks) {
      const int v = t.vertIndex();
      if (v < 0 || size_t(v) >= vertices.size() || vertices[v].noParent())
        continue;
      daughterEnergy[static_cast<unsigned int>(vertices[v].parentIndex())] += t.momentum().E();
    }
    auto pf = std::make_unique<reco::GenParticleCollection>();
    auto pfIdx = std::make_unique<std::vector<int>>();
    auto pfKind = std::make_unique<std::vector<int>>();
    for (size_t i = 0; i < tracks.size(); ++i) {
      const SimTrack& t = tracks[i];
      const auto& mom = t.momentum();
      const int a = std::abs(t.type());
      if (a == 12 || a == 14 || a == 16)
        continue;
      auto itd = daughterEnergy.find(t.trackId());
      if (itd != daughterEnergy.end() && itd->second >= maxDaughterEnergyFraction_ * mom.E())
        continue;
      const int charge = static_cast<int>(std::lround(t.charge()));
      bool inTracker = true;
      const int v = t.vertIndex();
      if (v >= 0 && size_t(v) < vertices.size()) {
        const auto& pos = vertices[v].position();
        inTracker = std::hypot(pos.x(), pos.y()) < trackerMaxRadius_ && std::abs(pos.z()) < trackerMaxAbsZ_;
      }
      const bool trackable =
          charge != 0 && inTracker && std::abs(mom.eta()) < chargedMaxAbsEta_ && mom.pt() > chargedMinPt_;
      if (trackable) {
        pf->emplace_back(charge, math::XYZTLorentzVector(mom), math::XYZPoint(0, 0, 0), t.type(), 1, true);
        pfIdx->push_back(static_cast<int>(i));
        pfKind->push_back(1);
      } else {
        auto it = caloOfTrack.find(static_cast<int>(i));
        if (it == caloOfTrack.end())
          continue;
        pf->push_back((*calo)[it->second]);
        pfIdx->push_back(static_cast<int>(i));
        pfKind->push_back(charge == 0 ? 2 : 3);
      }
    }

    event.put(std::move(calo), "calo");
    event.put(std::move(caloIdx), "caloSimTrackIndex");
    event.put(std::move(caloE[ECAL]), "caloEcal");
    event.put(std::move(caloE[ES]), "caloEs");
    event.put(std::move(caloE[HCAL]), "caloHcal");
    event.put(std::move(caloE[HO]), "caloHo");
    event.put(std::move(caloE[HF]), "caloHf");
    event.put(std::move(caloN), "caloNCells");
    event.put(std::move(pf), "pf");
    event.put(std::move(pfIdx), "pfSimTrackIndex");
    event.put(std::move(pfKind), "pfKind");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> verticesToken_;
  edm::ESGetToken<CaloGeometry, CaloGeometryRecord> geomToken_;
  pico::CaloSimHits simHits_;
  double ecalCellThreshold_, hcalCellThreshold_;
  double chargedMaxAbsEta_, chargedMinPt_;
  double trackerMaxRadius_, trackerMaxAbsZ_, maxDaughterEnergyFraction_;
  bool verbose_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimCaloCandidateProducer);
