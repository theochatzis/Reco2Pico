#ifndef Reco2Pico_PicoProducer_PicoGenParticleRowMap_h
#define Reco2Pico_PicoProducer_PicoGenParticleRowMap_h
// Map every entry of the full reco::GenParticle collection to its row in a
// pruned copy (GenParticlePruner output, i.e. the collection the GenPart table
// is written from). Pruned particles are exact copies, so (pdgId, status, p4)
// identifies them; -1 marks particles that were pruned away.
#include <cstdint>
#include <unordered_map>
#include <vector>

#include "DataFormats/HepMCCandidate/interface/GenParticle.h"

namespace pico {
  struct GenKey {
    int pdgId;
    int status;
    float pt, eta, phi;
    bool operator==(const GenKey& o) const {
      return pdgId == o.pdgId && status == o.status && pt == o.pt && eta == o.eta && phi == o.phi;
    }
  };
  struct GenKeyHash {
    size_t operator()(const GenKey& k) const {
      size_t h = std::hash<int>()(k.pdgId) ^ (std::hash<int>()(k.status) << 1);
      h ^= std::hash<float>()(k.pt) << 2;
      h ^= std::hash<float>()(k.eta) << 3;
      h ^= std::hash<float>()(k.phi) << 4;
      return h;
    }
  };

  inline GenKey genKey(const reco::GenParticle& g) {
    return GenKey{g.pdgId(), g.status(), float(g.pt()), float(g.eta()), float(g.phi())};
  }

  inline std::vector<int32_t> genParticleRowMap(const reco::GenParticleCollection& full,
                                                const reco::GenParticleCollection& pruned) {
    std::unordered_map<GenKey, int32_t, GenKeyHash> rows;
    rows.reserve(pruned.size());
    for (size_t i = 0; i < pruned.size(); ++i)
      rows.emplace(genKey(pruned[i]), static_cast<int32_t>(i));
    std::vector<int32_t> map(full.size(), -1);
    for (size_t i = 0; i < full.size(); ++i) {
      auto it = rows.find(genKey(full[i]));
      if (it != rows.end())
        map[i] = it->second;
    }
    return map;
  }
}  // namespace pico

#endif
