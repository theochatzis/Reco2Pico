# TruthGraph: the CMSSW MC-truth graph and what Reco2Pico takes from it

The CMSSW truth graph (`PhysicsTools/TruthInfo`, author Felice Pantaleo) and
the Reco2Pico sim tables answer the same question: what is the truth object
behind a reconstructed one, once Geant4 has decayed, converted and showered
the generator particles? This note summarises the graph as of
[cms-sw/cmssw#51829](https://github.com/cms-sw/cmssw/pull/51829) (open,
last updated 15 Oct 2026), compares it with our calorimeter-entrance
construction ([TrueJES.md](TrueJES.md), section 1.1), and lists the ideas taken
from it. Numbers quoted from the PR are its own measurements, on Phase-2
samples; numbers from our samples say so.

## 1. What the graph is

Three layers, built in this order:

1. **`TruthGraph`** (raw): a compressed sparse-row graph built from HepMC and
   the `g4SimHits` SimTracks and SimVertices.
2. **`truth::Graph`** (logical): a bipartite particle <-> vertex graph that
   merges the GEN and SIM parts where they can be matched safely, with
   navigation (`parents()`, `descendants()`, `firstCommonAncestor()`,
   `hasAncestorPdgId()`, ...). Every GEN-only vertex carries a reason
   (`HardScatter`, `ShowerBranching`, `Hadronization`, `Decay`).
3. **`truth::LogicalGraphHitIndex`**: per particle, its own sim hits and the
   hits of its whole subgraph (the particle and all its descendants), laid out
   so that a subgraph's hits are one contiguous, DetId-sorted range.

On top of it:

* **`truth::Branch`**: a view of a root particle plus a closure of its
  descendants (`Subtree`, `StableLeaves`, `DepthN`, `UntilPdgId`,
  `UntilLevels`, `Predicate`), with its four-momentum, visible and invisible
  energy, heavy-flavour content and hits. Branches are recomputed on demand,
  never stored.
* **Truth levels** (cmssw#51716): named rules that pick the truth objects of
  an event. A level must be an *antichain*: no member is an ancestor of
  another, so the same energy is never counted twice. The levels are
  `stableLegsFromInitialState`, `hardProcess`, `stableDecayProducts`,
  `caloBoundary`, `reconstructableFromSignal`, `underlyingEvent`,
  `partonJets`, `bHadrons`, `cHadrons`, `reconstructableFinalState`,
  `tauVisibleHadronic` and `tauVisibleLeptonic`.
* **The association layer** (cmssw#51829, this PR): reco <-> truth maps for
  tracks, tracksters, primary and secondary vertices and barrel PF clusters.

The package targets **Phase 2 (Run 4) only**. Its README states that there is
no Run-2 or Run-3 support, and the release workflows schedule it through the
`enableTruth` process modifier, which every Run-4 era carries.

## 2. The association layer of #51829

**Matching by hits.** A truth object owns the sim hits of its subgraph. A
reconstructed object owns the hits or clusters it was built from. Two scores
are computed from the shared hits or the shared energy: how much of the reco
object the truth object explains, and how much of the truth object the reco
object recovers. In the calorimeters every cell is weighted by its
reconstructed energy, as the TICL associators do: the reco object owns its
cluster fraction of the rechit energy, the truth object its sim fraction, and
a cell with a rechit but no sim hit counts against the reco object.

**Adaptive working points.** Which truth object a reco object should match
depends on the event. A pi0 whose two photons are reconstructed separately
should match the photons, and a merged pair should match the pi0. The search
starts at the directly matching particle and climbs the decay chain while the
larger subgraph still explains the reco object, and stops where the match is
best. The working points are `Fixed` (no climbing), `AdaptiveTight` and
`AdaptiveNominal`. By construction a working point changes *which* truth
object a reco object matches, never *whether* it matches. The fake rate is the
same at every working point, so a change in purity measures the truth
definition alone. The PR reports purity 0.34 at `Fixed` and 0.86 at
`AdaptiveNominal` for tracks on 200 TenTau events without pile-up, at an
unchanged fake rate. The climbing only lands on detector particles
(`assignableRoots`): partons, W, Z, H and synthetic nodes are barred, since a
subgraph that large covers any reco object.

**Tracker matching by cell.** A tracker DetId names a module, so two
particles crossing the same module share it. The PR keys the inner-tracker
truth by the digi channel, from the DigiSimLinks. On 20 ttbar events at PU200
it reports 99.54% agreement with `QuickTrackAssociatorByHits` matching by
cell, against 93.21% by module. A match lands on an unrelated particle
0.04% of the time by cell, against 5.50% by module.

**DQM.** Efficiency, duplicate and split rates are booked per truth level.
Fake rate, purity and pile-up rate are booked per working point. The axes
include the calorimeter-entrance eta, the size of the truth object and its
depth in the graph.

**Defects fixed in passing.** These are fixed in code that #51716 merged.
The mixed graph gave pile-up particles signal momenta, because it read
SimTracks by bare `trackId` instead of `(eventId, trackId)`. Equal association
scores went to an ancestor. A cycle could silently empty a truth level. The
configurations read the `Cleaned` instance of the barrel PFRecHits, which
holds the hits that failed the quality tests. We key tracks by
`(EncodedEventId, trackId)` (`pico::trackKey`) and do not read the `Cleaned`
instance, so neither of those two affects us.

## 3. Same information, different simulation settings

The graph is built from the same Geant4 record as our tables: SimTracks,
SimVertices and sim hits. It recovers nothing that the event does not store.
Two simulation settings differ between Phase 2 and our Run-3 samples, and
they decide how complete that record is.

**`SaveCaloBoundaryInformation`.** The tracker/calorimeter crossing is
recorded on every track that crosses (`SteppingAction`). But only a track that
is saved anyway keeps it, and in Run 3 the flag is set only on generator
primaries and unstored chains: a stored secondary born in the tracker already
has its own calorimeter-surface id and never gets it. Phase 2 sets
`SaveCaloBoundaryInformation = True` (`phase2_hgcal` modifier), which saves
every crossing track with its momentum at the face. That is why the
`caloBoundary` level can be "crossing recorded, not backscattered" there,
while our `isEntrance` needs the hit-ownership rules. It is also why our
`SimBoundaryJet` falls back to the production momentum for the Geant4 decay
and conversion products.

**`ReconnectDroppedAncestors`.** g4SimHits drops intermediate ancestors below
`PersistencyEmin`. Without reconnection, the production vertex of a stored
descendant then has `parentIndex = -1`, and the track is cut off from the
generator. CMSSW master sets `TrackingAction.ReconnectDroppedAncestors =
True`, which reattaches such a vertex to its nearest stored ancestor. It is
not in CMSSW_15_0_4 or 15_0_18, so our Run-3 samples have such orphans. It is
in CMSSW_20_1_0_pre4, the release of our Phase-2 line, where the orphan
handling below should find almost nothing to do. On
DY (`run3_rawsim` v4, 200 events): 1829 orphans out of 156,609 non-primary
SimTracks (1.2%), 92% of them born outside the tracker volume. The 1119
orphan entrance particles carried 0.75% of the entrance energy.

## 4. How it maps onto our construction

| TruthGraph | Reco2Pico |
|---|---|
| `caloBoundary` level | calorimeter-entrance particles (`SimTrack_isEntrance`) |
| subgraph hits of a particle | `SimTrack_entranceIdx` + `ownsCaloHits`, `SimCalo` deposits |
| antichain rule | every hit bookkept to exactly one entrance particle; entrance energy taken out of the parent's production momentum |
| `hardProcess`, `reconstructableFinalState`, `bHadrons`, ... | the rungs of the TrueJES ladder (`GenJet`, `SimJet`, ...) |
| adaptive climbing | choosing the ladder rung (the truth reference) per jet |
| rechit-energy-weighted shared energy | `RECHIT_SCALE` and the cell sharing in `PFCandTruth` |
| `(eventId, trackId)` keys, pile-up subgraphs | `pico::trackKey`, `picoMixedTruth`, `picoCaloEntrancePU` |

The two differ in what they produce. The graph associates individual reco
objects (tracks, clusters, vertices) with truth objects. TrueJES builds a
*jet* per truth level and measures the response between levels.

## 5. Ideas taken

**Done: orphans** (`PicoCaloEntrance.h`, `SimTrack_isOrphan`). A stored track
that is not a generator primary and has no stored parent is flagged. Its real
ancestor is unknown and already carries its energy. An orphan born outside
the tracker therefore keeps its hits (`SimCalo` counts them once) but gets zero
entrance and face momenta, so it is not clustered into `SimJet` or
`SimBoundaryJet` again. On 50 DY GEN-SIM events this takes 0.82% of the
entrance energy out of the particle list. Remaining: an orphan born in the
tracker is judged on its own, and `SimPFCand` still uses the deposit of a
calorimeter-born orphan. That double-counts when the dropped ancestor came
from a tracked charged particle. See [TrueJES.md](TrueJES.md), section 1.1.

**Proposed:**

1. **Adaptive truth reference for TrueJES.** Choose the rung per reco jet by
   how well it is explained, as the working points do, and book purity
   separately from efficiency. Then the share of the response that only moves
   with the truth definition becomes visible.
2. **Count trackable particles by tracker layers.** Our ideal PF calls a
   charged particle trackable from acceptance cuts (|eta| < 2.5,
   pT > 0.5 GeV, born in the box). `mix:MergedTrackTruth` is already in our
   files and carries `numberOfTrackerLayers` for the whole signal event.
3. **Tracker PSimHits for the face momentum.** The GEN-SIM-RAW tier keeps
   `*_g4SimHits_*_*` (`SimG4CoreRAW`), tracker PSimHits included; our RECO
   step drops them. The momentum at the outermost hit, propagated to the
   calorimeter face, would fill in the face momentum of the stored
   secondaries that the boundary flag misses. Checked on the DY
   GEN-SIM-RAW file: every `TrackerHits*` collection is there, as are
   `CaloHitsTk` and the muon-system hits.
4. **Match tracks by cell** where we use track <-> TP links. This matters
   mainly at high pile-up and in jet cores.
5. **Phase-2 cross-check.** On the Phase-2 line (`main`), run the graph's
   associators next to our entrance particles and Sim jets.
   `PhysicsTools/TruthInfo` is already in CMSSW_20_1_0_pre4; the association
   layer of #51829 is not merged yet.
6. **Private Run-3 GEN-SIM** with `SaveCaloBoundaryInformation = True` (or
   `fineCalo`) and `ReconnectDroppedAncestors`, if the gaps above turn out to
   matter for the ladder.

## 6. What the Run-3 Geant4 record holds (reference)

Per SimTrack: PDG id, the production four-momentum, the Geant4 track id and
`EncodedEventId`, the production vertex index, the generator index (primaries
only), the boundary-crossing flag with the position and momentum there, and a
tracker-surface position and momentum. **CMSSW_15_0_X never fills the
tracker-surface fields** (`SimTrack_tkPt/Eta/Phi` read 0). There is no end
point, no list of daughters and no trajectory: the tree is vertex -> parent
id only. Per SimVertex: position, time, parent id and Geant4 process type.
Per PCaloHit: DetId, energy, EM fraction, time, depth, `EncodedEventId` and
the Geant4 id of the owning track.

Stored are the generator primaries, the decay products of primaries (flagged
primary in turn, so whole decay cascades are kept), their conversions,
tracks leaving tracker hits above 0.2 GeV, and the ancestry needed to book
hits. Products of nuclear interactions, bremsstrahlung photons, delta rays
and shower particles are not stored as such. Their calorimeter hits are
re-keyed to the nearest stored ancestor.
