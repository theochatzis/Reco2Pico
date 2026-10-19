// Calorimeter deposits of the Geant4 sim hits, bookkept per calorimeter-entrance
// particle ("sim clusters"), the cells themselves, and an ideal particle-flow
// candidate list built from them.
//
// Every PCaloHit carries the Geant4 id of the particle it is bookkept to
// (CaloSD stores the "id on the calo surface": the particle that entered the
// calorimeter, or a stored daughter born inside it, see PicoCaloEntrance.h).
// Each hit is assigned to the calorimeter-entrance particle of that id
// (the id itself or its entrance ancestor, from the "caloEntrance" product), so
// that the deposits of a K0S decaying in ECAL or of a pion interacting in HCAL
// with stored daughters are counted with the particle that entered, exactly
// once. No clustering is needed. Cells are summed over all particles first and
// an optional per-cell threshold is applied to the cell total (as a rechit
// threshold would), then the cell energy is shared between the contributing
// entrance particles in proportion to their deposits.
//
// HCAL hits are relabelled from the test numbering to HcalDetId (as the
// digitiser does) and converted to GeV-equivalent with the digitiser sampling
// factors; HF hits (photoelectrons) use the HF factors.
//
// Products (parallel vectors per collection):
//   calo        reco::GenParticleCollection  one massless candidate per entrance particle with
//                                            deposits: energy = sum of its deposits, direction =
//                                            energy-weighted cell direction
//   caloSimTrackIndex, caloEcal, caloEs, caloHcal, caloHo, caloHf, caloNCells, caloNOwners
//   cells       reco::GenParticleCollection  one massless candidate per cell above threshold:
//                                            energy = cell total, direction = cell centre
//   cellSub (0 ECAL, 1 ES, 2 HCAL, 3 HO, 4 HF), cellDetId,
//   cellShareBegin / cellShareTrack / cellShareEnergy   the entrance particles contributing
//                                            to every cell with their share (CSR layout:
//                                            shares of cell c are [begin[c], begin[c+1]))
//   pf          reco::GenParticleCollection  ideal PF: for every entrance particle, charged,
//                                            produced inside the tracker volume, inside the
//                                            acceptance and above chargedMinPt -> production
//                                            momentum as an entrance particle ("perfect
//                                            tracking"; prodPx.. of caloEntrance, so that the
//                                            energy of emitted entrance daughters is not
//                                            counted twice), otherwise -> its calorimeter
//                                            deposit (if any)
//   pfSimTrackIndex, pfKind (1 charged from momentum, 2 neutral from deposit,
//                            3 charged but not trackable, from deposit)
//
// With the pile-up truth of a classically mixed event (PicoMixedTruthProducer:
// pileupSimTracks / pileupSimVertices / pileupCaloEntrance / pileupHits set):
//   cellPUEnergy, cellOotEnergy, cellNPU   per "cells" entry: in-time pile-up deposit, out-of-time
//                                          deposit and number of pile-up interactions in the cell
//   cellOotBx   std::vector<float>, 10 entries per "cells" entry: the out-of-time deposit of the
//               crossings -5 .. +3 one by one, then the sum of the earlier ones (< -5): the
//               crossings a pulse fit can confuse with the in-time one
//   cellsPU     reco::GenParticleCollection  one candidate per cell above threshold on the in-time
//                                            total (signal + pile-up), energy = that total
//   cellPUSub, cellPUDetId, cellPUShareBegin / cellPUShareTrack / cellPUShareEnergy  (signal shares)
//   caloPU      reco::GenParticleCollection  the deposits of the pile-up entrance particles
//   caloPUSimTrackIndex (index in the pileup SimTrack container), caloPUEvent (interaction number)
//   pfPU        reco::GenParticleCollection  the ideal PF of signal + in-time pile-up: pf followed by
//                                            the pile-up particles (charged trackable from momentum,
//                                            the others from their deposit)
//   pfPUSimTrackIndex (signal row or -1), pfPUKind (signal 1/2/3, pile-up 11/12/13)
//   pfPUCHS     reco::GenParticleCollection  the same without the trackable charged pile-up
//                                            particles: a perfect charged-hadron subtraction
//   pfPUCHSSimTrackIndex, pfPUCHSKind
#include <cmath>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/DetId/interface/DetId.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/Math/interface/LorentzVector.h"
#include "Geometry/CaloGeometry/interface/CaloGeometry.h"
#include "Geometry/Records/interface/CaloGeometryRecord.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoCaloEntrance.h"
#include "PicoCaloSimHits.h"

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
        verbose_(cfg.getUntrackedParameter<bool>("verbose", false)) {
    const edm::InputTag tag = cfg.getParameter<edm::InputTag>("caloEntrance");
    isEntranceToken_ = consumes<std::vector<int>>(edm::InputTag(tag.label(), "isEntrance"));
    entranceOfToken_ = consumes<std::vector<int>>(edm::InputTag(tag.label(), "entranceOf"));
    for (const char* c : {"prodPx", "prodPy", "prodPz", "prodE"})
      prodTokens_.push_back(consumes<std::vector<float>>(edm::InputTag(tag.label(), c)));
    pileup_ = !cfg.getParameter<edm::InputTag>("pileupSimTracks").label().empty();
    if (pileup_) {
      puTracksToken_ = consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("pileupSimTracks"));
      puVerticesToken_ = consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("pileupSimVertices"));
      const std::string pe = cfg.getParameter<edm::InputTag>("pileupCaloEntrance").label();
      puIsEntranceToken_ = consumes<std::vector<int>>(edm::InputTag(pe, "isEntrance"));
      puEntranceOfToken_ = consumes<std::vector<int>>(edm::InputTag(pe, "entranceOf"));
      for (const char* c : {"prodPx", "prodPy", "prodPz", "prodE"})
        puProdTokens_.push_back(consumes<std::vector<float>>(edm::InputTag(pe, c)));
      produces<std::vector<float>>("cellPUEnergy");
      produces<std::vector<float>>("cellOotEnergy");
      produces<std::vector<int>>("cellNPU");
      produces<std::vector<float>>("cellOotBx");
      produces<reco::GenParticleCollection>("cellsPU");
      produces<std::vector<int>>("cellPUSub");
      produces<std::vector<unsigned int>>("cellPUDetId");
      produces<std::vector<int>>("cellPUShareBegin");
      produces<std::vector<int>>("cellPUShareTrack");
      produces<std::vector<float>>("cellPUShareEnergy");
      produces<reco::GenParticleCollection>("caloPU");
      produces<std::vector<int>>("caloPUSimTrackIndex");
      produces<std::vector<int>>("caloPUEvent");
      produces<reco::GenParticleCollection>("pfPU");
      produces<std::vector<int>>("pfPUSimTrackIndex");
      produces<std::vector<int>>("pfPUKind");
      produces<reco::GenParticleCollection>("pfPUCHS");
      produces<std::vector<int>>("pfPUCHSSimTrackIndex");
      produces<std::vector<int>>("pfPUCHSKind");
    }
    produces<reco::GenParticleCollection>("calo");
    produces<std::vector<int>>("caloSimTrackIndex");
    produces<std::vector<float>>("caloEcal");
    produces<std::vector<float>>("caloEs");
    produces<std::vector<float>>("caloHcal");
    produces<std::vector<float>>("caloHo");
    produces<std::vector<float>>("caloHf");
    produces<std::vector<int>>("caloNCells");
    produces<std::vector<int>>("caloNOwners");
    produces<reco::GenParticleCollection>("cells");
    produces<std::vector<int>>("cellSub");
    produces<std::vector<unsigned int>>("cellDetId");
    produces<std::vector<int>>("cellShareBegin");
    produces<std::vector<int>>("cellShareTrack");
    produces<std::vector<float>>("cellShareEnergy");
    produces<reco::GenParticleCollection>("pf");
    produces<std::vector<int>>("pfSimTrackIndex");
    produces<std::vector<int>>("pfKind");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("caloEntrance", edm::InputTag("picoCaloEntrance"));
    desc.add<edm::InputTag>("pileupSimTracks", edm::InputTag(""));
    desc.add<edm::InputTag>("pileupSimVertices", edm::InputTag(""));
    desc.add<edm::InputTag>("pileupCaloEntrance", edm::InputTag(""));
    pico::CaloSimHits::fillDescription(desc);
    desc.add<double>("ecalCellThreshold", 0.0);
    desc.add<double>("hcalCellThreshold", 0.0);
    desc.add<double>("chargedMaxAbsEta", 2.5);
    desc.add<double>("chargedMinPt", 0.5);
    desc.add<double>("trackerMaxRadius", 123.0);
    desc.add<double>("trackerMaxAbsZ", 293.0);
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
    std::map<int, double> owners;  // hit-owning SimTrack rows merged into this particle
    double total() const { return e[ECAL] + e[ES] + e[HCAL] + e[HO] + e[HF]; }
  };

  void produce(edm::Event& event, const edm::EventSetup& setup) override {
    const auto& tracks = event.get(tracksToken_);
    const auto& vertices = event.get(verticesToken_);
    const auto& isEntrance = event.get(isEntranceToken_);
    const auto& entranceOf = event.get(entranceOfToken_);
    std::vector<const std::vector<float>*> prod;
    for (const auto& tok : prodTokens_)
      prod.push_back(&event.get(tok));
    if (isEntrance.size() != tracks.size() || entranceOf.size() != tracks.size())
      throw cms::Exception("LogicError") << "caloEntrance products do not match the SimTrack collection";
    const CaloGeometry& geom = setup.getData(geomToken_);
    std::unordered_map<unsigned int, int> rowOfTrackId;
    for (size_t i = 0; i < tracks.size(); ++i)
      rowOfTrackId.emplace(tracks[i].trackId(), static_cast<int>(i));
    auto particleOf = [&](int owner) { return entranceOf[owner] >= 0 ? entranceOf[owner] : owner; };

    // ---- pile-up truth (optional) ------------------------------------------------
    const edm::SimTrackContainer* puTracks = nullptr;
    const edm::SimVertexContainer* puVertices = nullptr;
    const std::vector<int>* puIsEntrance = nullptr;
    const std::vector<int>* puEntranceOf = nullptr;
    std::vector<const std::vector<float>*> puProd;
    std::unordered_map<uint64_t, int> rowOfPUTrackKey;
    if (pileup_) {
      puTracks = &event.get(puTracksToken_);
      puVertices = &event.get(puVerticesToken_);
      puIsEntrance = &event.get(puIsEntranceToken_);
      puEntranceOf = &event.get(puEntranceOfToken_);
      for (const auto& tok : puProdTokens_)
        puProd.push_back(&event.get(tok));
      if (puIsEntrance->size() != puTracks->size() || puEntranceOf->size() != puTracks->size())
        throw cms::Exception("LogicError") << "pileupCaloEntrance products do not match the pile-up SimTrack collection";
      for (size_t i = 0; i < puTracks->size(); ++i)
        rowOfPUTrackKey.emplace(pico::trackKey((*puTracks)[i]), static_cast<int>(i));
    }
    auto puParticleOf = [&](int owner) { return (*puEntranceOf)[owner] >= 0 ? (*puEntranceOf)[owner] : owner; };

    // ---- cells: sum over particles, keep per-particle shares ---------------------
    std::map<uint32_t, pico::CellShares> cells[NSUB];
    simHits_.build(event, setup, rowOfTrackId, cells, pileup_ ? &rowOfPUTrackKey : nullptr);
    if (verbose_) {
      for (int sub = 0; sub < NSUB; ++sub) {
        double tot = 0;
        for (const auto& kv : cells[sub])
          tot += kv.second.total;
        edm::LogPrint("PicoSimCalo") << "sub " << sub << " cells " << cells[sub].size() << " GeV-equivalent " << tot;
      }
    }

    // ---- per-particle deposits and cell candidates with the cell threshold ------
    std::map<int, Deposit> deposits;    // entrance SimTrack row -> deposit
    std::map<int, Deposit> depositsPU;  // pile-up entrance SimTrack row -> deposit
    auto cellCands = std::make_unique<reco::GenParticleCollection>();
    auto cellSub = std::make_unique<std::vector<int>>();
    auto cellDetId = std::make_unique<std::vector<unsigned int>>();
    auto cellShareBegin = std::make_unique<std::vector<int>>(1, 0);
    auto cellShareTrack = std::make_unique<std::vector<int>>();
    auto cellShareEnergy = std::make_unique<std::vector<float>>();
    auto cellPUEnergy = std::make_unique<std::vector<float>>();
    auto cellOotEnergy = std::make_unique<std::vector<float>>();
    auto cellNPU = std::make_unique<std::vector<int>>();
    auto cellOotBx = std::make_unique<std::vector<float>>();
    auto cellPUCands = std::make_unique<reco::GenParticleCollection>();
    auto cellPUSub = std::make_unique<std::vector<int>>();
    auto cellPUDetId = std::make_unique<std::vector<unsigned int>>();
    auto cellPUShareBegin = std::make_unique<std::vector<int>>(1, 0);
    auto cellPUShareTrack = std::make_unique<std::vector<int>>();
    auto cellPUShareEnergy = std::make_unique<std::vector<float>>();
    for (int sub = 0; sub < NSUB; ++sub) {
      const double threshold = (sub == ECAL || sub == ES) ? ecalCellThreshold_ : hcalCellThreshold_;
      for (const auto& kv : cells[sub]) {
        const bool signalCell = kv.second.total > 0 && kv.second.total >= threshold;
        const bool puCell = pileup_ && kv.second.all() > 0 && kv.second.all() >= threshold;
        if (!signalCell && !puCell)
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
        const double ux = pos.x() / r, uy = pos.y() / r, uz = pos.z() / r;
        // signal shares per entrance particle (several hit owners may map to the same particle)
        std::map<int, double> shares;
        for (const auto& tk : kv.second.perTrack) {
          const int p = particleOf(tk.first);
          shares[p] += tk.second;
          if (signalCell)
            deposits[p].owners[tk.first] += tk.second;
        }
        if (signalCell) {
          double cellTotal = 0;
          for (const auto& sh : shares) {
            Deposit& d = deposits[sh.first];
            d.e[sub] += sh.second;
            d.dx += sh.second * ux;
            d.dy += sh.second * uy;
            d.dz += sh.second * uz;
            d.nCells += 1;
            cellTotal += sh.second;
            cellShareTrack->push_back(sh.first);
            cellShareEnergy->push_back(sh.second);
          }
          cellShareBegin->push_back(static_cast<int>(cellShareTrack->size()));
          cellCands->emplace_back(0, math::XYZTLorentzVector(cellTotal * ux, cellTotal * uy, cellTotal * uz, cellTotal),
                                  math::XYZPoint(0, 0, 0), 0, 1, true);
          cellSub->push_back(sub);
          cellDetId->push_back(kv.first);
          if (pileup_) {
            cellPUEnergy->push_back(kv.second.puTotal);
            cellOotEnergy->push_back(kv.second.oot);
            cellNPU->push_back(static_cast<int>(kv.second.puPerEvent.size()));
            float early = 0;
            float byBx[9] = {0, 0, 0, 0, 0, 0, 0, 0, 0};
            for (const auto& bx : kv.second.ootPerBx) {
              if (bx.first < -5)
                early += bx.second;
              else if (bx.first >= -5 && bx.first <= 3 && bx.first != 0)
                byBx[bx.first + 5] += bx.second;
            }
            for (float v : byBx)
              cellOotBx->push_back(v);
            cellOotBx->push_back(early);
          }
        }
        if (puCell) {
          // the cell as a rechit would see it: signal + in-time pile-up; signal shares for the matching
          const double all = kv.second.all();
          for (const auto& sh : shares) {
            cellPUShareTrack->push_back(sh.first);
            cellPUShareEnergy->push_back(sh.second);
          }
          cellPUShareBegin->push_back(static_cast<int>(cellPUShareTrack->size()));
          cellPUCands->emplace_back(0, math::XYZTLorentzVector(all * ux, all * uy, all * uz, all), math::XYZPoint(0, 0, 0), 0, 1, true);
          cellPUSub->push_back(sub);
          cellPUDetId->push_back(kv.first);
          // deposits of the pile-up entrance particles (threshold on the cell total, as for the signal)
          std::map<int, double> puShares;
          for (const auto& tk : kv.second.perPUTrack)
            puShares[puParticleOf(tk.first)] += tk.second;
          for (const auto& sh : puShares) {
            Deposit& d = depositsPU[sh.first];
            d.e[sub] += sh.second;
            d.dx += sh.second * ux;
            d.dy += sh.second * uy;
            d.dz += sh.second * uz;
            d.nCells += 1;
          }
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
    auto caloNOwners = std::make_unique<std::vector<int>>();
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
      caloNOwners->push_back(static_cast<int>(d.owners.size()));
    }

    // ---- ideal PF candidates ---------------------------------------------------
    auto pf = std::make_unique<reco::GenParticleCollection>();
    auto pfIdx = std::make_unique<std::vector<int>>();
    auto pfKind = std::make_unique<std::vector<int>>();
    for (size_t i = 0; i < tracks.size(); ++i) {
      if (!isEntrance[i])
        continue;
      const SimTrack& t = tracks[i];
      const math::XYZTLorentzVectorD mom((*prod[0])[i], (*prod[1])[i], (*prod[2])[i], (*prod[3])[i]);
      const int a = std::abs(t.type());
      if (a == 12 || a == 14 || a == 16)
        continue;
      const int charge = static_cast<int>(std::lround(t.charge()));
      bool inTracker = true;
      const int v = t.vertIndex();
      if (v >= 0 && size_t(v) < vertices.size()) {
        const auto& pos = vertices[v].position();
        inTracker = std::hypot(pos.x(), pos.y()) < trackerMaxRadius_ && std::abs(pos.z()) < trackerMaxAbsZ_;
      }
      const bool trackable =
          charge != 0 && inTracker && mom.E() > 0 && std::abs(mom.eta()) < chargedMaxAbsEta_ && mom.pt() > chargedMinPt_;
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

    // ---- pile-up candidates and the ideal PF with pile-up -----------------------
    if (pileup_) {
      auto caloPU = std::make_unique<reco::GenParticleCollection>();
      auto caloPUIdx = std::make_unique<std::vector<int>>();
      auto caloPUEvent = std::make_unique<std::vector<int>>();
      std::unordered_map<int, size_t> caloPUOfTrack;
      for (const auto& kv : depositsPU) {
        const Deposit& d = kv.second;
        const double etot = d.total();
        const double norm = std::sqrt(d.dx * d.dx + d.dy * d.dy + d.dz * d.dz);
        if (etot <= 0 || norm <= 0)
          continue;
        const SimTrack& t = (*puTracks)[kv.first];
        math::XYZTLorentzVector p4(etot * d.dx / norm, etot * d.dy / norm, etot * d.dz / norm, etot);
        caloPUOfTrack[kv.first] = caloPU->size();
        caloPU->emplace_back(static_cast<int>(std::lround(t.charge())), p4, math::XYZPoint(0, 0, 0), t.type(), 1, true);
        caloPUIdx->push_back(kv.first);
        caloPUEvent->push_back(t.eventId().event());
      }
      auto pfPU = std::make_unique<reco::GenParticleCollection>(*pf);
      auto pfPUIdx = std::make_unique<std::vector<int>>(*pfIdx);
      auto pfPUKind = std::make_unique<std::vector<int>>(*pfKind);
      auto pfPUCHS = std::make_unique<reco::GenParticleCollection>(*pf);
      auto pfPUCHSIdx = std::make_unique<std::vector<int>>(*pfIdx);
      auto pfPUCHSKind = std::make_unique<std::vector<int>>(*pfKind);
      for (size_t i = 0; i < puTracks->size(); ++i) {
        if (!(*puIsEntrance)[i])
          continue;
        const SimTrack& t = (*puTracks)[i];
        const math::XYZTLorentzVectorD mom((*puProd[0])[i], (*puProd[1])[i], (*puProd[2])[i], (*puProd[3])[i]);
        const int a = std::abs(t.type());
        if (a == 12 || a == 14 || a == 16)
          continue;
        const int charge = static_cast<int>(std::lround(t.charge()));
        bool inTracker = true;
        const int v = t.vertIndex();
        if (v >= 0 && size_t(v) < puVertices->size()) {
          const auto& pos = (*puVertices)[v].position();
          inTracker = std::hypot(pos.x(), pos.y()) < trackerMaxRadius_ && std::abs(pos.z()) < trackerMaxAbsZ_;
        }
        const bool trackable =
            charge != 0 && inTracker && mom.E() > 0 && std::abs(mom.eta()) < chargedMaxAbsEta_ && mom.pt() > chargedMinPt_;
        if (trackable) {
          pfPU->emplace_back(charge, math::XYZTLorentzVector(mom), math::XYZPoint(0, 0, 0), t.type(), 1, true);
          pfPUIdx->push_back(-1);
          pfPUKind->push_back(11);  // a perfect charged-hadron subtraction removes these
        } else {
          auto it = caloPUOfTrack.find(static_cast<int>(i));
          if (it == caloPUOfTrack.end())
            continue;
          const int kind = charge == 0 ? 12 : 13;
          pfPU->push_back((*caloPU)[it->second]);
          pfPUIdx->push_back(-1);
          pfPUKind->push_back(kind);
          pfPUCHS->push_back((*caloPU)[it->second]);
          pfPUCHSIdx->push_back(-1);
          pfPUCHSKind->push_back(kind);
        }
      }
      event.put(std::move(cellPUEnergy), "cellPUEnergy");
      event.put(std::move(cellOotEnergy), "cellOotEnergy");
      event.put(std::move(cellNPU), "cellNPU");
      event.put(std::move(cellOotBx), "cellOotBx");
      event.put(std::move(cellPUCands), "cellsPU");
      event.put(std::move(cellPUSub), "cellPUSub");
      event.put(std::move(cellPUDetId), "cellPUDetId");
      event.put(std::move(cellPUShareBegin), "cellPUShareBegin");
      event.put(std::move(cellPUShareTrack), "cellPUShareTrack");
      event.put(std::move(cellPUShareEnergy), "cellPUShareEnergy");
      event.put(std::move(caloPU), "caloPU");
      event.put(std::move(caloPUIdx), "caloPUSimTrackIndex");
      event.put(std::move(caloPUEvent), "caloPUEvent");
      event.put(std::move(pfPU), "pfPU");
      event.put(std::move(pfPUIdx), "pfPUSimTrackIndex");
      event.put(std::move(pfPUKind), "pfPUKind");
      event.put(std::move(pfPUCHS), "pfPUCHS");
      event.put(std::move(pfPUCHSIdx), "pfPUCHSSimTrackIndex");
      event.put(std::move(pfPUCHSKind), "pfPUCHSKind");
    }

    event.put(std::move(calo), "calo");
    event.put(std::move(caloIdx), "caloSimTrackIndex");
    event.put(std::move(caloE[ECAL]), "caloEcal");
    event.put(std::move(caloE[ES]), "caloEs");
    event.put(std::move(caloE[HCAL]), "caloHcal");
    event.put(std::move(caloE[HO]), "caloHo");
    event.put(std::move(caloE[HF]), "caloHf");
    event.put(std::move(caloN), "caloNCells");
    event.put(std::move(caloNOwners), "caloNOwners");
    event.put(std::move(cellCands), "cells");
    event.put(std::move(cellSub), "cellSub");
    event.put(std::move(cellDetId), "cellDetId");
    event.put(std::move(cellShareBegin), "cellShareBegin");
    event.put(std::move(cellShareTrack), "cellShareTrack");
    event.put(std::move(cellShareEnergy), "cellShareEnergy");
    event.put(std::move(pf), "pf");
    event.put(std::move(pfIdx), "pfSimTrackIndex");
    event.put(std::move(pfKind), "pfKind");
  }

private:
  edm::EDGetTokenT<edm::SimTrackContainer> tracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> verticesToken_;
  edm::EDGetTokenT<std::vector<int>> isEntranceToken_, entranceOfToken_;
  std::vector<edm::EDGetTokenT<std::vector<float>>> prodTokens_;
  bool pileup_ = false;
  edm::EDGetTokenT<edm::SimTrackContainer> puTracksToken_;
  edm::EDGetTokenT<edm::SimVertexContainer> puVerticesToken_;
  edm::EDGetTokenT<std::vector<int>> puIsEntranceToken_, puEntranceOfToken_;
  std::vector<edm::EDGetTokenT<std::vector<float>>> puProdTokens_;
  edm::ESGetToken<CaloGeometry, CaloGeometryRecord> geomToken_;
  pico::CaloSimHits simHits_;
  double ecalCellThreshold_, hcalCellThreshold_;
  double chargedMaxAbsEta_, chargedMinPt_;
  double trackerMaxRadius_, trackerMaxAbsZ_;
  bool verbose_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoSimCaloCandidateProducer);
