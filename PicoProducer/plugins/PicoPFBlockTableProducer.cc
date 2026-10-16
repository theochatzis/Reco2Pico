// Pico tables describing the particle-flow block structure of an event:
//   <name>Elem  (instance "elements")      one row per PFBlockElement of every block
//   <name>Link  (instance "links")         one row per stored element-element link
//   PFCandElem  (instance "candElements")  one row per (PFCandidate, element) pair
//
// Indices refer to rows of the other Pico tables of the same job: Track
// (trackTableMinPt), PFCand (candMinPt) and the PFCluster<X> tables
// (clusterMinEnergy); raw keys into the original collections are kept too so
// nothing is lost when a referenced object was filtered out of those tables.
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidate.h"
#include "DataFormats/ParticleFlowCandidate/interface/PFCandidateFwd.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlock.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockFwd.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElement.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElementTrack.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElementGsfTrack.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElementBrem.h"
#include "DataFormats/ParticleFlowReco/interface/PFBlockElementSuperCluster.h"
#include "DataFormats/ParticleFlowReco/interface/PFCluster.h"
#include "DataFormats/ParticleFlowReco/interface/PFClusterFwd.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/GsfTrackReco/interface/GsfTrack.h"
#include "DataFormats/GsfTrackReco/interface/GsfTrackFwd.h"
#include "DataFormats/MuonReco/interface/Muon.h"
#include "DataFormats/MuonReco/interface/MuonFwd.h"
#include "DataFormats/EgammaReco/interface/SuperCluster.h"

class PicoPFBlockTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PicoPFBlockTableProducer(const edm::ParameterSet& cfg)
      : blocksToken_(consumes<reco::PFBlockCollection>(cfg.getParameter<edm::InputTag>("blocks"))),
        candsToken_(consumes<reco::PFCandidateCollection>(cfg.getParameter<edm::InputTag>("candidates"))),
        tracksToken_(consumes<reco::TrackCollection>(cfg.getParameter<edm::InputTag>("tracks"))),
        gsfToken_(consumes<reco::GsfTrackCollection>(cfg.getParameter<edm::InputTag>("gsfTracks"))),
        muonsToken_(consumes<reco::MuonCollection>(cfg.getParameter<edm::InputTag>("muons"))),
        name_(cfg.getParameter<std::string>("name")),
        candName_(cfg.getParameter<std::string>("candElementsName")),
        candMinPt_(cfg.getParameter<double>("candMinPt")),
        trackTableMinPt_(cfg.getParameter<double>("trackTableMinPt")),
        clusterMinEnergy_(cfg.getParameter<double>("clusterMinEnergy")),
        writeLinks_(cfg.getParameter<bool>("writeLinks")) {
    for (const auto& pset : cfg.getParameter<std::vector<edm::ParameterSet>>("clusters")) {
      clusterTokens_.push_back(consumes<reco::PFClusterCollection>(pset.getParameter<edm::InputTag>("src")));
      clusterCodes_.push_back(pset.getParameter<int32_t>("code"));
      clusterDoc_ += (clusterDoc_.empty() ? "" : ", ") + std::to_string(pset.getParameter<int32_t>("code")) + "=" +
                     pset.getParameter<std::string>("table");
    }
    produces<nanoaod::FlatTable>("elements");
    produces<nanoaod::FlatTable>("links");
    produces<nanoaod::FlatTable>("candElements");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("blocks", edm::InputTag("particleFlowBlock"));
    desc.add<edm::InputTag>("candidates", edm::InputTag("particleFlow"));
    desc.add<edm::InputTag>("tracks", edm::InputTag("generalTracks"));
    desc.add<edm::InputTag>("gsfTracks", edm::InputTag("electronGsfTracks"));
    desc.add<edm::InputTag>("muons", edm::InputTag("muons"));
    desc.add<std::string>("name", "PFBlock");
    desc.add<std::string>("candElementsName", "PFCandElem");
    desc.add<double>("candMinPt", 0.0);
    desc.add<double>("trackTableMinPt", 0.0);
    desc.add<double>("clusterMinEnergy", 0.0);
    desc.add<bool>("writeLinks", true);
    edm::ParameterSetDescription cluster;
    cluster.add<edm::InputTag>("src");
    cluster.add<int32_t>("code");
    cluster.add<std::string>("table");
    desc.addVPSet("clusters", cluster, std::vector<edm::ParameterSet>());
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& blocks = event.get(blocksToken_);
    const auto& cands = event.get(candsToken_);
    edm::Handle<reco::TrackCollection> tracks;
    edm::Handle<reco::GsfTrackCollection> gsfTracks;
    edm::Handle<reco::MuonCollection> muons;
    event.getByToken(tracksToken_, tracks);
    event.getByToken(gsfToken_, gsfTracks);
    event.getByToken(muonsToken_, muons);
    edm::Handle<reco::PFBlockCollection> blocksHandle;
    event.getByToken(blocksToken_, blocksHandle);

    // Row maps of the filtered Pico tables.
    std::vector<int32_t> trackRow(tracks->size(), -1);
    for (size_t i = 0, row = 0; i < tracks->size(); ++i)
      if ((*tracks)[i].pt() >= trackTableMinPt_)
        trackRow[i] = row++;

    struct ClusterInfo {
      edm::ProductID id;
      int32_t code;
      std::vector<int32_t> row;
    };
    std::vector<ClusterInfo> clusterInfos;
    for (size_t c = 0; c < clusterTokens_.size(); ++c) {
      edm::Handle<reco::PFClusterCollection> h;
      event.getByToken(clusterTokens_[c], h);
      if (!h.isValid())
        continue;
      ClusterInfo info;
      info.id = h.id();
      info.code = clusterCodes_[c];
      info.row.assign(h->size(), -1);
      for (size_t i = 0, row = 0; i < h->size(); ++i)
        if ((*h)[i].energy() >= clusterMinEnergy_)
          info.row[i] = row++;
      clusterInfos.push_back(std::move(info));
    }

    // ---- elements -------------------------------------------------------
    std::vector<int32_t> eBlock, eIdx, eType, eTrackIdx, eTrackKey, eClusterTable, eClusterIdx, eClusterKey, eGsfKey,
        eMuonKey, eScKey, eTrackTypeBits, eCandIdx, eNCands;
    std::vector<float> ePt, eEta, ePhi, eEnergy, eEcalEntEta, eEcalEntPhi, eTime, eTimeErr, eDeltaP;
    std::vector<uint8_t> eLinkedToDisp, eHasConv, eHasV0, eScFromGsf, eScFromPhoton;
    std::vector<size_t> blockOffset(blocks.size() + 1, 0);
    for (size_t b = 0; b < blocks.size(); ++b)
      blockOffset[b + 1] = blockOffset[b] + blocks[b].elements().size();
    const size_t nElem = blockOffset.back();
    auto reserveAll = [nElem](auto&... v) { (v.reserve(nElem), ...); };
    reserveAll(eBlock, eIdx, eType, eTrackIdx, eTrackKey, eClusterTable, eClusterIdx, eClusterKey, eGsfKey, eMuonKey,
               eScKey, eTrackTypeBits, eCandIdx, eNCands, ePt, eEta, ePhi, eEnergy, eEcalEntEta, eEcalEntPhi, eTime,
               eTimeErr, eDeltaP, eLinkedToDisp, eHasConv, eHasV0, eScFromGsf, eScFromPhoton);

    for (size_t b = 0; b < blocks.size(); ++b) {
      const auto& elements = blocks[b].elements();
      for (size_t i = 0; i < elements.size(); ++i) {
        const reco::PFBlockElement& el = elements[i];
        eBlock.push_back(b);
        eIdx.push_back(i);
        eType.push_back(static_cast<int32_t>(el.type()));

        int32_t trackIdx = -1, trackKey = -1, clusterTable = 0, clusterIdx = -1, clusterKey = -1;
        int32_t gsfKey = -1, muonKey = -1, scKey = -1;
        float pt = -1.f, eta = 0.f, phi = 0.f, energy = -1.f, ecalEta = 0.f, ecalPhi = 0.f, deltaP = 0.f;
        uint8_t scFromGsf = 0, scFromPhoton = 0;

        const auto& tref = el.trackRef();
        if (tref.isNonnull() && tref.isAvailable()) {
          trackKey = tref.key();
          if (tref.id() == tracks.id() && tref.key() < trackRow.size())
            trackIdx = trackRow[tref.key()];
          pt = tref->pt();
          eta = tref->eta();
          phi = tref->phi();
          energy = tref->p();
        }
        const auto& cref = el.clusterRef();
        if (cref.isNonnull() && cref.isAvailable()) {
          clusterKey = cref.key();
          for (const auto& info : clusterInfos) {
            if (info.id == cref.id()) {
              clusterTable = info.code;
              if (cref.key() < info.row.size())
                clusterIdx = info.row[cref.key()];
              break;
            }
          }
          pt = cref->pt();
          eta = cref->eta();
          phi = cref->phi();
          energy = cref->energy();
        }
        const auto& mref = el.muonRef();
        if (mref.isNonnull() && mref.isAvailable() && mref.id() == muons.id())
          muonKey = mref.key();

        if (el.type() == reco::PFBlockElement::TRACK) {
          const auto* tr = dynamic_cast<const reco::PFBlockElementTrack*>(&el);
          if (tr) {
            ecalEta = tr->positionAtECALEntrance().eta();
            ecalPhi = tr->positionAtECALEntrance().phi();
          }
        } else if (el.type() == reco::PFBlockElement::GSF) {
          const auto* gsf = dynamic_cast<const reco::PFBlockElementGsfTrack*>(&el);
          if (gsf) {
            const auto& gref = gsf->GsftrackRef();
            if (gref.isNonnull() && gref.isAvailable() && gref.id() == gsfTracks.id())
              gsfKey = gref.key();
            pt = gsf->Pin().pt();
            eta = gsf->Pin().eta();
            phi = gsf->Pin().phi();
            energy = gsf->Pin().energy();
            ecalEta = gsf->positionAtECALEntrance().eta();
            ecalPhi = gsf->positionAtECALEntrance().phi();
          }
        } else if (el.type() == reco::PFBlockElement::BREM) {
          const auto* brem = dynamic_cast<const reco::PFBlockElementBrem*>(&el);
          if (brem) {
            const auto& gref = brem->GsftrackRef();
            if (gref.isNonnull() && gref.isAvailable() && gref.id() == gsfTracks.id())
              gsfKey = gref.key();
            deltaP = brem->DeltaP();
          }
        } else if (el.type() == reco::PFBlockElement::SC) {
          const auto* sc = dynamic_cast<const reco::PFBlockElementSuperCluster*>(&el);
          if (sc) {
            const auto& sref = sc->superClusterRef();
            if (sref.isNonnull() && sref.isAvailable()) {
              scKey = sref.key();
              energy = sref->energy();
              eta = sref->eta();
              phi = sref->phi();
              pt = energy / std::cosh(eta);
            }
            scFromGsf = sc->fromGsfElectron() ? 1 : 0;
            scFromPhoton = sc->fromPhoton() ? 1 : 0;
          }
        }

        int32_t typeBits = 0;
        for (int t = reco::PFBlockElement::DEFAULT; t <= reco::PFBlockElement::T_FROM_V0; ++t)
          if (el.trackType(static_cast<reco::PFBlockElement::TrackType>(t)))
            typeBits |= (1 << t);

        eTrackIdx.push_back(trackIdx);
        eTrackKey.push_back(trackKey);
        eClusterTable.push_back(clusterTable);
        eClusterIdx.push_back(clusterIdx);
        eClusterKey.push_back(clusterKey);
        eGsfKey.push_back(gsfKey);
        eMuonKey.push_back(muonKey);
        eScKey.push_back(scKey);
        eTrackTypeBits.push_back(typeBits);
        eLinkedToDisp.push_back(el.isLinkedToDisplacedVertex() ? 1 : 0);
        eHasConv.push_back(el.convRefs().empty() ? 0 : 1);
        eHasV0.push_back(el.V0Ref().isNonnull() ? 1 : 0);
        eScFromGsf.push_back(scFromGsf);
        eScFromPhoton.push_back(scFromPhoton);
        ePt.push_back(pt);
        eEta.push_back(eta);
        ePhi.push_back(phi);
        eEnergy.push_back(energy);
        eEcalEntEta.push_back(ecalEta);
        eEcalEntPhi.push_back(ecalPhi);
        eTime.push_back(el.isTimeValid() ? el.time() : -999.f);
        eTimeErr.push_back(el.timeError());
        eDeltaP.push_back(deltaP);
        eCandIdx.push_back(-1);
        eNCands.push_back(0);
      }
    }

    // ---- candidate -> element map ----------------------------------------
    std::vector<int32_t> cCand, cBlock, cElem, cElemRow, cType;
    int32_t candRow = 0;
    for (const auto& cand : cands) {
      if (cand.pt() < candMinPt_)
        continue;
      for (const auto& eib : cand.elementsInBlocks()) {
        const reco::PFBlockRef& bref = eib.first;
        int32_t blockIdx = -1, elemRow = -1, type = 0;
        if (bref.isNonnull() && bref.isAvailable() && bref.id() == blocksHandle.id()) {
          blockIdx = bref.key();
          if (eib.second < bref->elements().size()) {
            elemRow = blockOffset[blockIdx] + eib.second;
            type = static_cast<int32_t>(bref->elements()[eib.second].type());
            if (eCandIdx[elemRow] < 0)
              eCandIdx[elemRow] = candRow;
            ++eNCands[elemRow];
          }
        }
        cCand.push_back(candRow);
        cBlock.push_back(blockIdx);
        cElem.push_back(eib.second);
        cElemRow.push_back(elemRow);
        cType.push_back(type);
      }
      ++candRow;
    }

    // ---- links -------------------------------------------------------------
    std::vector<int32_t> lBlock, lElem1, lElem2, lRow1, lRow2, lTest;
    std::vector<float> lDist;
    if (writeLinks_) {
      for (size_t b = 0; b < blocks.size(); ++b) {
        const unsigned n = blocks[b].elements().size();
        for (const auto& kv : blocks[b].linkData()) {
          unsigned i1 = 0, i2 = 0;
          if (!decodeLink(kv.first, n, i1, i2))
            continue;
          lBlock.push_back(b);
          lElem1.push_back(i1);
          lElem2.push_back(i2);
          lRow1.push_back(blockOffset[b] + i1);
          lRow2.push_back(blockOffset[b] + i2);
          lDist.push_back(kv.second.distance);
          lTest.push_back(static_cast<int32_t>(kv.second.test));
        }
      }
    }

    auto elemTable = std::make_unique<nanoaod::FlatTable>(eBlock.size(), name_ + "Elem", false, false);
    elemTable->setDoc("reco::PFBlockElement of every reco::PFBlock (" + blocksLabelDoc() + ")");
    elemTable->addColumn<int32_t>("blockIdx", eBlock, "index of the PFBlock in the block collection");
    elemTable->addColumn<int32_t>("elemIdx", eIdx, "index of the element inside its block");
    elemTable->addColumn<int32_t>("type", eType,
                                  "PFBlockElement::Type: 1 TRACK, 2 PS1, 3 PS2, 4 ECAL, 5 HCAL, 6 GSF, 7 BREM, 8 HFEM, 9 HFHAD, 10 SC, 11 HO, 12 HGCAL");
    elemTable->addColumn<float>("pt", ePt, "pt of the linked object (track, cluster, GSF Pin, SC); -1 if none", 10);
    elemTable->addColumn<float>("eta", eEta, "eta of the linked object", 10);
    elemTable->addColumn<float>("phi", ePhi, "phi of the linked object", 10);
    elemTable->addColumn<float>("energy", eEnergy, "energy (cluster, SC) or momentum (track, GSF) of the linked object", 10);
    elemTable->addColumn<int32_t>("trackIdx", eTrackIdx, "row in the Track table (-1: no track or filtered out)");
    elemTable->addColumn<int32_t>("trackKey", eTrackKey, "key into the generalTracks collection (-1: none)");
    elemTable->addColumn<int32_t>("clusterTable", eClusterTable, "PFCluster table of clusterIdx: 0 none, " + clusterDoc_);
    elemTable->addColumn<int32_t>("clusterIdx", eClusterIdx, "row in the PFCluster table given by clusterTable (-1: none or filtered out)");
    elemTable->addColumn<int32_t>("clusterKey", eClusterKey, "key into the PFCluster collection (-1: none)");
    elemTable->addColumn<int32_t>("gsfTrackKey", eGsfKey, "key into electronGsfTracks for GSF/BREM elements (-1: none)");
    elemTable->addColumn<int32_t>("muonKey", eMuonKey, "key into the muons collection for track elements identified as muons (-1: none)");
    elemTable->addColumn<int32_t>("superClusterKey", eScKey, "key into the SuperCluster collection for SC elements (-1: none)");
    elemTable->addColumn<int32_t>("trackTypeBits", eTrackTypeBits,
                                  "bit i set when trackType(i): 0 DEFAULT, 1 T_FROM_DISP, 2 T_TO_DISP, 3 T_FROM_GAMMACONV, 4 MUON, 5 T_FROM_V0");
    elemTable->addColumn<uint8_t>("linkedToDisplacedVertex", eLinkedToDisp, "isLinkedToDisplacedVertex()");
    elemTable->addColumn<uint8_t>("hasConversion", eHasConv, "element carries conversion references");
    elemTable->addColumn<uint8_t>("hasV0", eHasV0, "element carries a V0 reference");
    elemTable->addColumn<uint8_t>("scFromGsfElectron", eScFromGsf, "SC element: fromGsfElectron()");
    elemTable->addColumn<uint8_t>("scFromPhoton", eScFromPhoton, "SC element: fromPhoton()");
    elemTable->addColumn<float>("ecalEntranceEta", eEcalEntEta, "TRACK/GSF: eta of the extrapolated position at the ECAL entrance", 10);
    elemTable->addColumn<float>("ecalEntrancePhi", eEcalEntPhi, "TRACK/GSF: phi of the extrapolated position at the ECAL entrance", 10);
    elemTable->addColumn<float>("bremDeltaP", eDeltaP, "BREM: DeltaP of the bremsstrahlung tangent", 10);
    elemTable->addColumn<float>("time", eTime, "element time (-999 if not valid)", 10);
    elemTable->addColumn<float>("timeError", eTimeErr, "element time uncertainty (<0: not valid)", 10);
    elemTable->addColumn<int32_t>("candIdx", eCandIdx, "row in the PFCand table of the first candidate using this element (-1: unused)");
    elemTable->addColumn<int32_t>("nCands", eNCands, "number of PFCand rows using this element");

    auto linkTable = std::make_unique<nanoaod::FlatTable>(lBlock.size(), name_ + "Link", false, false);
    linkTable->setDoc("stored element-element links (PFBlock::linkData) of every reco::PFBlock");
    linkTable->addColumn<int32_t>("blockIdx", lBlock, "index of the PFBlock in the block collection");
    linkTable->addColumn<int32_t>("elem1", lElem1, "index of the first element inside the block");
    linkTable->addColumn<int32_t>("elem2", lElem2, "index of the second element inside the block");
    linkTable->addColumn<int32_t>("elemRow1", lRow1, "row of the first element in the " + name_ + "Elem table");
    linkTable->addColumn<int32_t>("elemRow2", lRow2, "row of the second element in the " + name_ + "Elem table");
    linkTable->addColumn<float>("distance", lDist, "link distance (PFBlock::Link::distance)", 10);
    linkTable->addColumn<int32_t>("test", lTest, "PFBlock::LinkTest used for the link (0 RECHIT, 1 NLINKTEST, 2 ALL)");

    auto candTable = std::make_unique<nanoaod::FlatTable>(cCand.size(), candName_, false, false);
    candTable->setDoc("PFCandidate -> PFBlockElement pairs (reco::PFCandidate::elementsInBlocks)");
    candTable->addColumn<int32_t>("candIdx", cCand, "row in the PFCand table");
    candTable->addColumn<int32_t>("blockIdx", cBlock, "index of the PFBlock in the block collection (-1: not the configured collection)");
    candTable->addColumn<int32_t>("elemIdx", cElem, "index of the element inside the block");
    candTable->addColumn<int32_t>("elemRow", cElemRow, "row in the " + name_ + "Elem table (-1: unresolved)");
    candTable->addColumn<int32_t>("type", cType, "PFBlockElement::Type of the element (0: unresolved)");

    event.put(std::move(elemTable), "elements");
    event.put(std::move(linkTable), "links");
    event.put(std::move(candTable), "candElements");
  }

private:
  // Inverse of reco::PFBlock::matrix2vector: index = base(i) + (j - i - 1),
  // base(i) = i*n - i*(i+1)/2 for the upper triangle i < j.
  static bool decodeLink(unsigned index, unsigned n, unsigned& i, unsigned& j) {
    if (n < 2)
      return false;
    for (unsigned a = 0; a + 1 < n; ++a) {
      const unsigned base = a * n - a * (a + 1) / 2;
      const unsigned rowLength = n - 1 - a;
      if (index < base + rowLength) {
        i = a;
        j = index - base + a + 1;
        return j < n;
      }
    }
    return false;
  }

  std::string blocksLabelDoc() const { return "element types, object links and candidate usage"; }

  edm::EDGetTokenT<reco::PFBlockCollection> blocksToken_;
  edm::EDGetTokenT<reco::PFCandidateCollection> candsToken_;
  edm::EDGetTokenT<reco::TrackCollection> tracksToken_;
  edm::EDGetTokenT<reco::GsfTrackCollection> gsfToken_;
  edm::EDGetTokenT<reco::MuonCollection> muonsToken_;
  std::vector<edm::EDGetTokenT<reco::PFClusterCollection>> clusterTokens_;
  std::vector<int32_t> clusterCodes_;
  std::string clusterDoc_;
  std::string name_;
  std::string candName_;
  double candMinPt_;
  double trackTableMinPt_;
  double clusterMinEnergy_;
  bool writeLinks_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PicoPFBlockTableProducer);
