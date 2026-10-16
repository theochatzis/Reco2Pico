#ifndef Reco2Pico_PicoProducer_PicoSimAncestry_h
#define Reco2Pico_PicoProducer_PicoSimAncestry_h
// Geant4 ancestry helpers: the generator primary every SimTrack descends from
// (through the stored SimVertex parent links) and the gen jet every generator
// particle is a constituent of.
#include <unordered_map>
#include <vector>

#include "DataFormats/Common/interface/Handle.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/JetReco/interface/Jet.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include "PicoGenParticleRowMap.h"

namespace pico {

  // index into genParticles of the generator ancestor of every SimTrack (-1: none)
  inline std::vector<int> ancestorGenParticle(const edm::SimTrackContainer& tracks,
                                              const edm::SimVertexContainer& vertices,
                                              const reco::GenParticleCollection& gens) {
    std::unordered_map<unsigned int, int> rowOfTrackId;
    for (size_t i = 0; i < tracks.size(); ++i)
      rowOfTrackId.emplace(tracks[i].trackId(), static_cast<int>(i));
    auto parentOf = [&](int i) -> int {
      const int v = tracks[i].vertIndex();
      if (v < 0 || size_t(v) >= vertices.size() || vertices[v].noParent())
        return -1;
      auto it = rowOfTrackId.find(static_cast<unsigned int>(vertices[v].parentIndex()));
      return it == rowOfTrackId.end() ? -1 : it->second;
    };
    std::vector<int> out(tracks.size(), -1);
    for (size_t i = 0; i < tracks.size(); ++i) {
      int cur = static_cast<int>(i), guard = 0;
      while (cur >= 0 && tracks[cur].noGenpart() && guard++ < 10000)
        cur = parentOf(cur);
      if (cur >= 0 && !tracks[cur].noGenpart()) {
        const int k = tracks[cur].genpartIndex() - 1;
        if (k >= 0 && size_t(k) < gens.size() && gens[k].pdgId() == tracks[cur].type())
          out[i] = k;
      }
    }
    return out;
  }

  // gen jet index of every genParticles entry (-1: not a constituent)
  inline std::vector<int> genJetOfParticle(const edm::View<reco::Jet>& genJets,
                                           const edm::Handle<reco::GenParticleCollection>& gensHandle) {
    const auto& gens = *gensHandle;
    std::vector<int> out(gens.size(), -1);
    for (size_t j = 0; j < genJets.size(); ++j) {
      const reco::Jet& jet = genJets[j];
      for (unsigned d = 0; d < jet.numberOfDaughters(); ++d) {
        const auto ptr = jet.daughterPtr(d);
        int k = -1;
        if (ptr.isNonnull() && ptr.id() == gensHandle.id())
          k = ptr.key();
        else if (ptr.isNonnull() && ptr.isAvailable()) {
          const reco::GenParticle* gp = dynamic_cast<const reco::GenParticle*>(ptr.get());
          if (gp) {
            auto key = genKey(*gp);
            for (size_t m = 0; m < gens.size(); ++m)
              if (genKey(gens[m]) == key) {
                k = m;
                break;
              }
          }
        }
        if (k >= 0)
          out[k] = j;
      }
    }
    return out;
  }

}  // namespace pico

#endif
