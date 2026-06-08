#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <tuple>
#include <vector>
#include <limits>

#include "DataFormats/Candidate/interface/Candidate.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include "Geometry/HcalCommonData/interface/HcalDDDRecConstants.h"
#include "Geometry/Records/interface/HcalRecNumberingRecord.h"

class PFRhoStripTableProducer : public edm::stream::EDProducer<> {
public:
  explicit PFRhoStripTableProducer(const edm::ParameterSet&);
  ~PFRhoStripTableProducer() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  enum Flavor : unsigned int {
    kAll = 0,
    kChargedHadron,
    kNeutralHadron,
    kPhoton,
    kElectron,
    kMuon,
    kOther,
    kNFlavors
  };

  struct Strip {
    int etaBin = 0;  // Generic eta-bin identifier: signed HCAL ieta for HCAL geometry, 0-based index otherwise.
    int phiBin = 0;  // Generic phi-bin identifier: HCAL iphi for HCAL geometry, 0-based index otherwise.
    int ieta = 0;    // HCAL ieta when useHCALGeometry=true, otherwise 0.
    int zside = 0;   // HCAL zside when useHCALGeometry=true, otherwise sign of eta-center.
    int iphi = 0;    // HCAL iphi when useHCALGeometry=true, otherwise 0.

    float etaMin = 0.f;
    float etaMax = 0.f;
    float phiMin = 0.f;
    float phiMax = 0.f;
    float eta = 0.f;
    float phi = 0.f;
    float dEta = 0.f;
    float dPhi = 0.f;
    float area = 0.f;

    std::array<float, kNFlavors> sumPt{};
    std::array<uint16_t, kNFlavors> n{};
  };

  void produce(edm::Event&, const edm::EventSetup&) override;

  std::vector<Strip> makeCustomStrips() const;
  std::vector<Strip> makeHCALStrips(const HcalDDDRecConstants&) const;

  int findStrip(const std::vector<Strip>& strips, float eta, float phi) const;
  static bool insidePhi(const Strip& strip, float phi);
  static float wrapPhi(float phi);
  static Flavor flavorOf(const reco::Candidate& cand);
  static int signOf(float x);
  static float median(std::vector<float> values);
  static void validateEdges(const std::vector<double>& edges, const std::string& name);

  const edm::EDGetTokenT<edm::View<reco::Candidate>> srcToken_;
  const edm::ESGetToken<HcalDDDRecConstants, HcalRecNumberingRecord> hcalToken_;

  const std::string tableName_;
  const bool useHCALGeometry_;
  const bool includeHB_;
  const bool includeHE_;
  const float minPt_;
  const std::vector<double> etaBins_;
  const std::vector<double> phiBins_;
};

PFRhoStripTableProducer::PFRhoStripTableProducer(const edm::ParameterSet& cfg)
    : srcToken_(consumes<edm::View<reco::Candidate>>(cfg.getParameter<edm::InputTag>("src"))),
      hcalToken_(esConsumes<HcalDDDRecConstants, HcalRecNumberingRecord>()),
      tableName_(cfg.getParameter<std::string>("name")),
      useHCALGeometry_(cfg.getParameter<bool>("useHCALGeometry")),
      includeHB_(cfg.getParameter<bool>("includeHB")),
      includeHE_(cfg.getParameter<bool>("includeHE")),
      minPt_(static_cast<float>(cfg.getParameter<double>("minPt"))),
      etaBins_(cfg.getParameter<std::vector<double>>("etaBins")),
      phiBins_(cfg.getParameter<std::vector<double>>("phiBins")) {
  if (!useHCALGeometry_) {
    validateEdges(etaBins_, "etaBins");
    validateEdges(phiBins_, "phiBins");

    if (phiBins_.front() < -M_PI - 1e-6 || phiBins_.back() > M_PI + 1e-6) {
      throw cms::Exception("Configuration")
          << "PFRhoStripTableProducer with useHCALGeometry=false expects phiBins inside [-pi, pi].";
    }
  }

  if (useHCALGeometry_ && !includeHB_ && !includeHE_) {
    throw cms::Exception("Configuration")
        << "PFRhoStripTableProducer has useHCALGeometry=true but both includeHB and includeHE are false.";
  }

  produces<nanoaod::FlatTable>();
}

void PFRhoStripTableProducer::validateEdges(const std::vector<double>& edges, const std::string& name) {
  if (edges.size() < 2) {
    throw cms::Exception("Configuration") << "PFRhoStripTableProducer requires at least two values in " << name << ".";
  }

  for (unsigned int i = 1; i < edges.size(); ++i) {
    if (!(edges[i] > edges[i - 1])) {
      throw cms::Exception("Configuration")
          << "PFRhoStripTableProducer requires strictly increasing " << name << ". Problem at index " << i << ".";
    }
  }
}

float PFRhoStripTableProducer::median(std::vector<float> values) {
  if (values.empty())
    return 0.f;

  std::sort(values.begin(), values.end());

  const unsigned int n = values.size();
  const unsigned int mid = n / 2;

  if (n % 2 == 1)
    return values[mid];

  return 0.5f * (values[mid - 1] + values[mid]);
}

int PFRhoStripTableProducer::signOf(float x) {
  if (x > 0.f)
    return 1;
  if (x < 0.f)
    return -1;
  return 0;
}

float PFRhoStripTableProducer::wrapPhi(float phi) {
  while (phi <= -M_PI)
    phi += 2.f * M_PI;
  while (phi > M_PI)
    phi -= 2.f * M_PI;
  return phi;
}

PFRhoStripTableProducer::Flavor PFRhoStripTableProducer::flavorOf(const reco::Candidate& cand) {
  const int absPdgId = std::abs(cand.pdgId());

  if (absPdgId == 11)
    return kElectron;
  if (absPdgId == 13)
    return kMuon;
  if (absPdgId == 22)
    return kPhoton;

  // For packedPFCandidates this separates the usual charged-hadron PF candidates
  // without requiring the concrete pat::PackedCandidate type.
  if (cand.charge() != 0)
    return kChargedHadron;

  // Common neutral-hadron PF pdgIds are 130, 2112, 310, 311, 3122.
  // The charge fallback keeps the producer usable with generic reco::Candidate views.
  if (absPdgId == 130 || absPdgId == 2112 || absPdgId == 310 || absPdgId == 311 || absPdgId == 3122 ||
      cand.charge() == 0)
    return kNeutralHadron;

  return kOther;
}

bool PFRhoStripTableProducer::insidePhi(const Strip& strip, float phi) {
  phi = wrapPhi(phi);

  // Custom bins are represented by explicit phiMin/phiMax edges.
  if (strip.phiMax > strip.phiMin) {
    const bool lastBin = std::abs(strip.phiMax - static_cast<float>(M_PI)) < 1e-5;
    if (lastBin)
      return phi >= strip.phiMin && phi <= strip.phiMax;
    return phi >= strip.phiMin && phi < strip.phiMax;
  }

  // HCAL bins are represented by center and width. This naturally handles the phi wrap-around.
  const float dphi = wrapPhi(phi - strip.phi);
  return std::abs(dphi) < 0.5f * strip.dPhi;
}

int PFRhoStripTableProducer::findStrip(const std::vector<Strip>& strips, float eta, float phi) const {
  int bestIdx = -1;

  float bestArea = std::numeric_limits<float>::max();
  float bestScore = std::numeric_limits<float>::max();

  phi = wrapPhi(phi);

  for (unsigned int i = 0; i < strips.size(); ++i) {
    const auto& strip = strips[i];

    const bool inEta =
        (eta >= strip.etaMin && eta < strip.etaMax) ||
        (std::abs(strip.etaMax - 3.0f) < 1e-5f && eta >= strip.etaMin && eta <= strip.etaMax) ||
        (std::abs(strip.etaMin + 3.0f) < 1e-5f && eta >= strip.etaMin && eta <= strip.etaMax);

    if (!inEta)
      continue;

    if (!insidePhi(strip, phi))
      continue;

    const float area = strip.area > 0.f ? strip.area : std::abs(strip.dEta * strip.dPhi);

    const float dEtaNorm = std::abs(eta - strip.eta) / std::max(std::abs(strip.dEta), 1e-6f);
    const float dPhiNorm = std::abs(wrapPhi(phi - strip.phi)) / std::max(std::abs(strip.dPhi), 1e-6f);
    const float score = dEtaNorm * dEtaNorm + dPhiNorm * dPhiNorm;

    const bool betterArea = area < bestArea - 1e-7f;
    const bool sameAreaBetterScore = std::abs(area - bestArea) < 1e-7f && score < bestScore;

    if (betterArea || sameAreaBetterScore) {
      bestArea = area;
      bestScore = score;
      bestIdx = static_cast<int>(i);
    }
  }

  return bestIdx;
}
std::vector<PFRhoStripTableProducer::Strip> PFRhoStripTableProducer::makeCustomStrips() const {
  std::vector<Strip> strips;
  strips.reserve((etaBins_.size() - 1) * (phiBins_.size() - 1));

  for (unsigned int ieta = 0; ieta + 1 < etaBins_.size(); ++ieta) {
    for (unsigned int iphi = 0; iphi + 1 < phiBins_.size(); ++iphi) {
      Strip strip;
      strip.etaBin = static_cast<int>(ieta);
      strip.phiBin = static_cast<int>(iphi);
      strip.ieta = 0;
      strip.iphi = 0;

      strip.etaMin = static_cast<float>(etaBins_[ieta]);
      strip.etaMax = static_cast<float>(etaBins_[ieta + 1]);

      // Keep explicit custom edges as given. In particular, do not wrap -pi to +pi,
      // otherwise the first bin [-pi, ...] would become ill-defined.
      strip.phiMin = static_cast<float>(phiBins_[iphi]);
      strip.phiMax = static_cast<float>(phiBins_[iphi + 1]);

      strip.eta = 0.5f * (strip.etaMin + strip.etaMax);
      strip.phi = wrapPhi(0.5f * (strip.phiMin + strip.phiMax));
      strip.dEta = strip.etaMax - strip.etaMin;
      strip.dPhi = strip.phiMax - strip.phiMin;
      strip.area = std::abs(strip.dEta * strip.dPhi);
      strip.zside = signOf(strip.eta);

      strips.push_back(strip);
    }
  }

  return strips;
}

std::vector<PFRhoStripTableProducer::Strip>
PFRhoStripTableProducer::makeHCALStrips(const HcalDDDRecConstants& hcal) const {
  std::map<std::tuple<int, int, int>, Strip> unique;

  auto addBins = [&](int hcalType) {
    // hcalType = 0 -> HB, 1 -> HE
    const auto etaBins = hcal.getEtaBins(hcalType);

    for (const auto& bin : etaBins) {
      for (const auto& phiPair : bin.phis) {
        Strip strip;
        strip.ieta = bin.ieta;
        strip.zside = bin.zside;
        strip.iphi = phiPair.first;
        strip.etaBin = strip.zside * strip.ieta;
        strip.phiBin = strip.iphi;

        if (bin.zside > 0) {
          strip.etaMin = static_cast<float>(bin.etaMin);
          strip.etaMax = static_cast<float>(bin.etaMax);
        } else {
          strip.etaMin = static_cast<float>(-bin.etaMax);
          strip.etaMax = static_cast<float>(-bin.etaMin);
        }

        strip.phi = wrapPhi(static_cast<float>(phiPair.second));
        strip.dPhi = static_cast<float>(bin.dphi);
        strip.phiMin = 0.f;
        strip.phiMax = 0.f;
        strip.eta = 0.5f * (strip.etaMin + strip.etaMax);
        strip.dEta = strip.etaMax - strip.etaMin;
        strip.area = std::abs(strip.dEta * strip.dPhi);

        // getEtaBins can return multiple depth/layer structures for the same eta-phi strip.
        // The rho strip map should contain one row per eta-phi strip, so deduplicate here.
        unique.emplace(std::make_tuple(strip.zside, strip.ieta, strip.iphi), strip);
      }
    }
  };

  if (includeHB_)
    addBins(0);
  if (includeHE_)
    addBins(1);

  std::vector<Strip> strips;
  strips.reserve(unique.size());
  for (const auto& item : unique)
    strips.push_back(item.second);

  std::sort(strips.begin(), strips.end(), [](const Strip& a, const Strip& b) {
    return std::tie(a.etaBin, a.phiBin) < std::tie(b.etaBin, b.phiBin);
  });

  return strips;
}

void PFRhoStripTableProducer::produce(edm::Event& event, const edm::EventSetup& setup) {
  std::vector<Strip> strips = useHCALGeometry_ ? makeHCALStrips(setup.getData(hcalToken_)) : makeCustomStrips();

  edm::Handle<edm::View<reco::Candidate>> src;
  event.getByToken(srcToken_, src);

  for (const auto& cand : *src) {
    if (cand.pt() < minPt_)
      continue;

    const int idx = findStrip(strips, static_cast<float>(cand.eta()), static_cast<float>(cand.phi()));
    if (idx < 0)
      continue;

    const float pt = static_cast<float>(cand.pt());
    const Flavor flavor = flavorOf(cand);

    strips[idx].sumPt[kAll] += pt;
    strips[idx].sumPt[flavor] += pt;
    ++strips[idx].n[kAll];
    ++strips[idx].n[flavor];
  }

  // Compute FastJet-like rho per eta ring:
  //   1. Compute each eta-phi strip density: sumPt / area.
  //   2. For each etaBin and each flavor, take the median over phi strips.
  // The rho columns below store this median value, repeated for all rows in the same etaBin.
  std::map<int, std::array<std::vector<float>, kNFlavors>> stripRhoValuesByEtaBin;

  for (const auto& strip : strips) {
    for (unsigned int f = 0; f < kNFlavors; ++f) {
      const float stripRho = strip.area > 0.f ? strip.sumPt[f] / strip.area : 0.f;
      stripRhoValuesByEtaBin[strip.etaBin][f].push_back(stripRho);
    }
  }

  std::map<int, std::array<float, kNFlavors>> medianRhoByEtaBin;

  for (auto& etaItem : stripRhoValuesByEtaBin) {
    const int etaBin = etaItem.first;
    auto& valuesByFlavor = etaItem.second;

    for (unsigned int f = 0; f < kNFlavors; ++f) {
      medianRhoByEtaBin[etaBin][f] = median(valuesByFlavor[f]);
    }
  }

  const unsigned int nRows = strips.size();

  std::vector<int> etaBin, phiBin, ieta, zside, iphi;
  std::vector<float> etaMin, etaMax, eta, phiMin, phiMax, phi, dEta, dPhi, area;

  std::array<std::vector<float>, kNFlavors> sumPt;
  std::array<std::vector<float>, kNFlavors> rho;
  std::array<std::vector<uint16_t>, kNFlavors> n;

  etaBin.reserve(nRows);
  phiBin.reserve(nRows);
  ieta.reserve(nRows);
  zside.reserve(nRows);
  iphi.reserve(nRows);
  etaMin.reserve(nRows);
  etaMax.reserve(nRows);
  eta.reserve(nRows);
  phiMin.reserve(nRows);
  phiMax.reserve(nRows);
  phi.reserve(nRows);
  dEta.reserve(nRows);
  dPhi.reserve(nRows);
  area.reserve(nRows);

  for (unsigned int f = 0; f < kNFlavors; ++f) {
    sumPt[f].reserve(nRows);
    rho[f].reserve(nRows);
    n[f].reserve(nRows);
  }

  for (const auto& strip : strips) {
    etaBin.push_back(strip.etaBin);
    phiBin.push_back(strip.phiBin);
    ieta.push_back(strip.ieta);
    zside.push_back(strip.zside);
    iphi.push_back(strip.iphi);
    etaMin.push_back(strip.etaMin);
    etaMax.push_back(strip.etaMax);
    eta.push_back(strip.eta);
    phiMin.push_back(strip.phiMin);
    phiMax.push_back(strip.phiMax);
    phi.push_back(strip.phi);
    dEta.push_back(strip.dEta);
    dPhi.push_back(strip.dPhi);
    area.push_back(strip.area);

    for (unsigned int f = 0; f < kNFlavors; ++f) {
      sumPt[f].push_back(strip.sumPt[f]);
      rho[f].push_back(medianRhoByEtaBin[strip.etaBin][f]);
      n[f].push_back(strip.n[f]);
    }
  }

  auto table = std::make_unique<nanoaod::FlatTable>(nRows, tableName_, false, false);
  table->setDoc("PF rho as the median eta-phi strip density per eta bin, optionally using physical HCAL HB/HE segmentation");
  
  constexpr int coordBits = 4;
  constexpr int rhoBits   = 4;
  constexpr int ptBits    = 6;

  table->addColumn<int>(
      "etaBin", etaBin, "generic eta-bin id: signed HCAL ieta if useHCALGeometry, otherwise custom eta-bin index");
  table->addColumn<int>(
      "phiBin", phiBin, "generic phi-bin id: HCAL iphi if useHCALGeometry, otherwise custom phi-bin index");
  table->addColumn<int>("iEta", ieta, "HCAL ieta when useHCALGeometry=true, otherwise 0");
  table->addColumn<int>("zside", zside, "HCAL zside when useHCALGeometry=true, otherwise sign of eta center");
  table->addColumn<int>("iPhi", iphi, "HCAL iphi when useHCALGeometry=true, otherwise 0");

  table->addColumn<float>("etaMin", etaMin, "lower eta edge", coordBits);
  table->addColumn<float>("etaMax", etaMax, "upper eta edge", coordBits);
  table->addColumn<float>("eta", eta, "eta center", coordBits);
  table->addColumn<float>("phiMin", phiMin, "lower phi edge for custom bins; 0 for HCAL geometry bins", coordBits);
  table->addColumn<float>("phiMax", phiMax, "upper phi edge for custom bins; 0 for HCAL geometry bins", coordBits);
  table->addColumn<float>("phi", phi, "phi center", coordBits);
  table->addColumn<float>("dEta", dEta, "eta bin width", coordBits);
  table->addColumn<float>("dPhi", dPhi, "phi bin width", coordBits);
  table->addColumn<float>("area", area, "eta-phi strip area", coordBits);

  table->addColumn<float>("sumPt", sumPt[kAll], "scalar PF pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>("rho", rho[kAll], "median PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>("n", n[kAll], "number of PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtChargedHadron", sumPt[kChargedHadron],
      "charged-hadron PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoChargedHadron", rho[kChargedHadron],
      "median charged-hadron PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nChargedHadron", n[kChargedHadron],
      "number of charged-hadron PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtNeutralHadron", sumPt[kNeutralHadron],
      "neutral-hadron PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoNeutralHadron", rho[kNeutralHadron],
      "median neutral-hadron PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nNeutralHadron", n[kNeutralHadron],
      "number of neutral-hadron PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtPhoton", sumPt[kPhoton],
      "photon PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoPhoton", rho[kPhoton],
      "median photon PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nPhoton", n[kPhoton],
      "number of photon PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtElectron", sumPt[kElectron],
      "electron PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoElectron", rho[kElectron],
      "median electron PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nElectron", n[kElectron],
      "number of electron PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtMuon", sumPt[kMuon],
      "muon PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoMuon", rho[kMuon],
      "median muon PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nMuon", n[kMuon],
      "number of muon PF candidates in this eta-phi strip");

  table->addColumn<float>(
      "sumPtOther", sumPt[kOther],
      "other PF scalar pT sum in this eta-phi strip", ptBits);
  table->addColumn<float>(
      "rhoOther", rho[kOther],
      "median other PF rho over phi strips in this eta bin", rhoBits);
  table->addColumn<uint16_t>(
      "nOther", n[kOther],
      "number of other PF candidates in this eta-phi strip");
  event.put(std::move(table));
}

void PFRhoStripTableProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src", edm::InputTag("packedPFCandidates"));
  desc.add<std::string>("name", "PFRhoStrip");
  desc.add<bool>("useHCALGeometry", true);
  desc.add<bool>("includeHB", true);
  desc.add<bool>("includeHE", true);
  desc.add<double>("minPt", 0.0);

  // Used only when useHCALGeometry=false.
  desc.add<std::vector<double>>("etaBins", std::vector<double>{});
  desc.add<std::vector<double>>("phiBins", std::vector<double>{});

  descriptions.add("pfRhoStripTable", desc);
}

DEFINE_FWK_MODULE(PFRhoStripTableProducer);
