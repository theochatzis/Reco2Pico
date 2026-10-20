#ifndef Reco2Pico_PicoProducer_PicoCaloEntrance_h
#define Reco2Pico_PicoProducer_PicoCaloEntrance_h
// The calorimeter-entrance particles of the Geant4 simulation: the cut through
// the stored decay tree at the tracker/calorimeter boundary.
//
// What Geant4 stores (SimG4Core MCTruthUtil, SimG4CMS CaloTrkProcessing,
// CaloSD):
//   * a stored secondary (decay or conversion product of a primary, flag > 0
//     in MCTruthUtil::secondary) gets its own "id on the calo surface" at
//     creation, wherever it is born; the unstored secondaries inherit the id
//     of their mother;
//   * CaloTrkProcessing sets the boundary-crossing flag (SimTrack::crossedBoundary,
//     with the position and momentum at the crossing) only for a track whose
//     id on the calo surface is still 0 when it steps into a calorimeter
//     volume, i.e. for primaries and unstored chains, never for a stored
//     secondary born in the tracker;
//   * every PCaloHit carries the id on the calo surface of the particle that
//     deposited it (CaloSD::getTrackID), so the hits of a stored daughter born
//     inside the calorimeter (the pions of a K0S decaying in ECAL) reference
//     the daughter, not the particle that entered;
//   * at the end of the event the hits of a particle that was not saved as a
//     SimTrack are re-keyed to its nearest saved ancestor (CaloSD::saveHit,
//     SimTrackManager::giveMotherNeeded), so a saved photon that converted in
//     the tracker, or a saved pi0, can own the hits of unsaved descendants,
//     while a saved secondary that inherited its mother's id (a bremsstrahlung
//     photon, a delta ray, a continuation entry of the same particle) owns
//     nothing: its hits are the mother's.
//
// Definition used here, top-down over the tree:
//   * a SimTrack born outside the tracker volume belongs to the entrance
//     particle of its parent when the parent has one (born in the
//     calorimeter: its hits are assigned to that ancestor); otherwise it is an
//     entrance particle itself if it owns hits (a bookkeeping fallback, rare);
//   * a SimTrack born inside the tracker volume is an entrance particle if it
//     crossed the boundary (flag) or "reaches the calorimeter": it owns
//     calorimeter sim hits, or a chain of daughters born outside the tracker
//     volume does (the K0S above, a photon converting in the last tracker
//     layers). A tracker-born daughter of an entrance particle (a
//     bremsstrahlung photon or a delta ray emitted before the face) is judged
//     on its own: it is a separate entrance particle if it reaches the
//     calorimeter, lost otherwise.
//   Everything else is before the boundary (decayed, converted or absorbed in
//   the tracker: replaced by its daughters or lost).
//
// Two momenta are given for every entrance particle:
//   * production: the production momentum, scaled down by the entrance energy
//     found in its tracker-born subtree: the energy of its tracker-born
//     daughters that are entrance particles themselves (the stored emissions,
//     decay and interaction products whose hits are their own), and
//     recursively of the entrance particles below a tracker-born daughter that
//     is not one (a product that decayed before the face, the continuation
//     entries Geant4 writes after each bremsstrahlung): E_left = E - taken
//     along the production direction, zero if nothing is left. Daughters
//     whose hits are bookkept to the parent are not subtracted, since their
//     energy is counted with the parent on the calorimeter side too. A scalar
//     energy balance is used rather than a four-vector subtraction because the
//     secondaries of a nuclear interaction carry target energy and go in other
//     directions.
//   * boundary: the momentum Geant4 recorded at the crossing when the flag is
//     set (after the energy loss and the bending in the tracker), the
//     production one otherwise.
// Nucleons and nuclei born at a hadronic interaction vertex (knocked out of
// the tracker material: their rest mass was not part of the energy that
// entered) are counted with their kinetic energy in both.
//
// Orphans: a stored SimTrack that is not a generator primary and has no stored
// parent (g4SimHits drops low-energy intermediate ancestors and, before
// TrackingAction.ReconnectDroppedAncestors, which is not in CMSSW_15_0_X,
// leaves the production vertex with parentIndex -1). Its real stored ancestor
// is unknown and already carries the orphan's energy in its own momentum. An
// orphan born outside the tracker volume therefore keeps its hits (it stays
// an entrance particle, so the deposits are counted once on the calorimeter
// side) but gets zero momenta, so that it is not clustered a second time into
// the jets of the entrance particles. Orphans born inside the tracker are
// judged as any other track.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "DataFormats/Math/interface/LorentzVector.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

namespace pico {

  // key of a Geant4 track across mixed events: (EncodedEventId, track id); the signal
  // event has EncodedEventId (0, 0), so its keys are the plain track ids
  inline uint64_t trackKey(uint32_t eventIdRaw, unsigned int trackId) {
    return (static_cast<uint64_t>(eventIdRaw) << 32) | static_cast<uint64_t>(trackId);
  }
  inline uint64_t trackKey(const SimTrack& t) { return trackKey(t.eventId().rawId(), t.trackId()); }

  struct CaloEntrance {
    std::vector<uint8_t> isEntrance;    // per SimTrack
    std::vector<uint8_t> ownsHits;      // per SimTrack: referenced by calorimeter sim hits
    std::vector<uint8_t> reachesCalo;   // per SimTrack: see above
    std::vector<uint8_t> bornInTracker; // per SimTrack: production vertex inside the tracker volume
    std::vector<int> entranceOf;        // per SimTrack: row of its entrance particle (itself or an ancestor), -1 none
    std::vector<int> parent;            // per SimTrack: row of the parent SimTrack, -1 none
    std::vector<uint8_t> orphan;        // per SimTrack: no stored parent and not a generator primary
    std::vector<math::XYZTLorentzVectorD> production;  // per SimTrack: production momentum as an entrance particle
    std::vector<math::XYZTLorentzVectorD> boundary;    // per SimTrack: momentum at the face (see above)
  };

  // nucleons and nuclei created by a hadronic interaction: knocked out of the material
  inline bool knockedOutNucleon(const SimTrack& t, const edm::SimVertexContainer& vertices) {
    const int pdg = t.type();
    if (!(pdg == 2112 || pdg == 2212 || pdg > 1000000000))
      return false;
    const int v = t.vertIndex();
    if (v < 0 || size_t(v) >= vertices.size())
      return false;
    const unsigned int proc = vertices[v].processType();  // G4 process sub-types
    return proc == 121 || proc == 131 || proc == 141 || proc == 151 || proc == 161;  // inelastic, capture, fission, at rest
  }

  // momentum with the rest mass removed from the energy (direction kept)
  inline math::XYZTLorentzVectorD kineticOnly(const math::XYZTLorentzVectorD& p4, double mass) {
    const double ek = p4.E() - mass;
    if (ek <= 0 || p4.E() <= 0)
      return math::XYZTLorentzVectorD(0, 0, 0, 0);
    return p4 * (ek / p4.E());
  }

  // hitTrackKeys: trackKey() of every track referenced by a calorimeter sim hit. The
  // containers may hold several mixed events (pile-up): tracks and vertices are
  // matched within their EncodedEventId.
  inline CaloEntrance caloEntrance(const edm::SimTrackContainer& tracks,
                                   const edm::SimVertexContainer& vertices,
                                   const std::unordered_set<uint64_t>& hitTrackKeys,
                                   double trackerMaxRadius,
                                   double trackerMaxAbsZ) {
    const size_t n = tracks.size();
    CaloEntrance out;
    out.isEntrance.assign(n, 0);
    out.ownsHits.assign(n, 0);
    out.reachesCalo.assign(n, 0);
    out.bornInTracker.assign(n, 1);
    out.entranceOf.assign(n, -1);
    out.parent.assign(n, -1);
    out.orphan.assign(n, 0);

    std::unordered_map<uint64_t, int> rowOfTrackKey;
    rowOfTrackKey.reserve(n);
    for (size_t i = 0; i < n; ++i)
      rowOfTrackKey.emplace(trackKey(tracks[i]), static_cast<int>(i));

    std::vector<std::vector<int>> children(n);
    for (size_t i = 0; i < n; ++i) {
      const SimTrack& t = tracks[i];
      out.ownsHits[i] = hitTrackKeys.count(trackKey(t)) ? 1 : 0;
      const int v = t.vertIndex();
      if (v >= 0 && size_t(v) < vertices.size()) {
        const auto& pos = vertices[v].position();
        out.bornInTracker[i] =
            (std::hypot(pos.x(), pos.y()) < trackerMaxRadius && std::abs(pos.z()) < trackerMaxAbsZ) ? 1 : 0;
        if (!vertices[v].noParent()) {
          auto it = rowOfTrackKey.find(trackKey(t.eventId().rawId(), static_cast<unsigned int>(vertices[v].parentIndex())));
          if (it != rowOfTrackKey.end() && it->second != static_cast<int>(i)) {
            out.parent[i] = it->second;
            children[it->second].push_back(static_cast<int>(i));
          }
        }
      }
      // no stored parent and not a generator primary
      out.orphan[i] = (out.parent[i] < 0 && t.noGenpart()) ? 1 : 0;
    }

    // bottom-up: reaches the calorimeter (through daughters born outside the tracker only)
    std::vector<int> order;  // post-order (children before parents)
    order.reserve(n);
    {
      std::vector<uint8_t> seen(n, 0);
      for (size_t root = 0; root < n; ++root) {
        if (out.parent[root] >= 0 || seen[root])
          continue;
        std::vector<std::pair<int, size_t>> stack{{static_cast<int>(root), 0}};
        seen[root] = 1;
        while (!stack.empty()) {
          auto& top = stack.back();
          if (top.second < children[top.first].size()) {
            const int c = children[top.first][top.second++];
            if (!seen[c]) {
              seen[c] = 1;
              stack.emplace_back(c, 0);
            }
          } else {
            order.push_back(top.first);
            stack.pop_back();
          }
        }
      }
      for (size_t i = 0; i < n; ++i)  // cycles or orphans (should not happen)
        if (!seen[i])
          order.push_back(static_cast<int>(i));
    }
    for (int i : order) {
      bool reaches = out.ownsHits[i] || tracks[i].crossedBoundary();
      if (!reaches)
        for (int c : children[i])
          if (!out.bornInTracker[c] && out.reachesCalo[c]) {
            reaches = true;
            break;
          }
      out.reachesCalo[i] = reaches ? 1 : 0;
    }

    // top-down: tracks born in the calorimeter belong to the entrance ancestor,
    // tracks born in the tracker are judged on their own
    for (auto it = order.rbegin(); it != order.rend(); ++it) {
      const int i = *it;
      const int p = out.parent[i];
      const int inherited = p >= 0 ? out.entranceOf[p] : -1;
      if (!out.bornInTracker[i] && inherited >= 0) {
        out.entranceOf[i] = inherited;
        continue;
      }
      const bool entrance = out.bornInTracker[i] ? (tracks[i].crossedBoundary() || out.reachesCalo[i]) : out.ownsHits[i];
      if (entrance) {
        out.isEntrance[i] = 1;
        out.entranceOf[i] = i;
      }
    }

    // base momenta: production, with knocked-out nucleons by their kinetic energy
    std::vector<math::XYZTLorentzVectorD> base(n);
    std::vector<uint8_t> kinetic(n, 0);
    for (size_t i = 0; i < n; ++i) {
      const SimTrack& t = tracks[i];
      kinetic[i] = knockedOutNucleon(t, vertices) ? 1 : 0;
      base[i] = kinetic[i] ? kineticOnly(t.momentum(), t.momentum().M()) : t.momentum();
    }
    // entrance energy in the tracker-born subtree of every track (children before parents)
    std::vector<double> subtreeE(n, 0.0), taken(n, 0.0);
    for (int i : order) {
      double sum = 0;
      for (int c : children[i])
        if (out.bornInTracker[c])
          sum += subtreeE[c];
      taken[i] = sum;
      subtreeE[i] = out.isEntrance[i] ? base[i].E() : sum;
    }
    out.production.resize(n);
    out.boundary.resize(n);
    for (size_t i = 0; i < n; ++i) {
      const SimTrack& t = tracks[i];
      const math::XYZTLorentzVectorD& p4 = base[i];
      const double left = p4.E() - taken[i];
      // a particle whose entrance daughters carry all of its energy (a pi0 whose photons
      // own their hits) keeps nothing: zero momentum, so that it is not clustered
      out.production[i] = (left <= 1e-6 || p4.E() <= 0) ? math::XYZTLorentzVectorD(0, 0, 0, 0) : p4 * (left / p4.E());
      if (t.crossedBoundary() && t.getMomentumAtBoundary().E() > 0) {
        math::XYZTLorentzVectorD b(t.getMomentumAtBoundary());
        out.boundary[i] = kinetic[i] ? kineticOnly(b, t.momentum().M()) : b;
      } else {
        out.boundary[i] = out.production[i];
      }
      // an orphan born in the calorimeter: its energy is already with its unknown ancestor
      if (out.orphan[i] && !out.bornInTracker[i]) {
        out.production[i] = math::XYZTLorentzVectorD(0, 0, 0, 0);
        out.boundary[i] = math::XYZTLorentzVectorD(0, 0, 0, 0);
      }
    }
    return out;
  }

}  // namespace pico

#endif
