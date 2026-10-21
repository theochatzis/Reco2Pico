# Pico production

## Chained batch processing

Use `bdriver -c first_cfg.py --steps steps.json` to run configurations in order.
The JSON lists subsequent steps; paths are relative to the JSON file:

```json
[
  {
    "cfg": "python/workflows/RECO_to_pico_cfg.py",
    "args": ["isMC=true", "era=Run3_2024", "globalTag=133X_mcRun3_2024_realistic_v10"]
  }
]
```

An optional `"cmssw": "/absolute/path/to/CMSSW_X_Y_Z"` selects a release area
for that step. Otherwise it uses the active `CMSSW_BASE` from job preparation,
even if the preceding step overrides its release. Areas must support the
submission `SCRAM_ARCH` and be accessible on the workers.

Each subsequent configuration must accept `inputFiles`, `secondaryInputFiles`,
`output`, `maxEvents`, and `skipEvents`. The driver owns these arguments.
Only the first step receives the event slice; later steps process its output
from the beginning. Additional command-line configuration arguments apply
only to the first step; use each JSON entry's `args` for later steps.

```bash
bdriver -c reco_cfg.py --customize-cfg --steps steps.json \
  -d /PRIMARY/PROCESSING/GEN-SIM-RAW -p 0 \
  -o jobs/raw_to_pico -fo root://hip-cms-se.csc.fi//store/user/USERNAME/picos \
  -n 100 --cpus 1 --memory 8G --disk-mb 20000 --time 02:00:00
```

Generate and validate `reco_cfg.py` with `cmsDriver.py` in the intended
reconstruction release first. `--customize-cfg` adapts the first configuration;
a generated configuration should have one output module. Reconstruction
settings and downstream conditions must match the sample and chosen releases.

The last output is always transferred as `out_N.root`. Add
`--save-intermediates` to also transfer `step1_out_N.root`, `step2_out_N.root`,
etc. Each intermediate is transferred or removed after its consumer succeeds.
The job is marked complete only after all steps and required transfers succeed.
Failed jobs are not resumed from saved intermediate files.

The resource values above are starting points for a small pilot, not measured
requirements. Request memory for the largest step, runtime for the complete
chain, and scratch space for adjacent outputs plus processing overhead.
CPU requests do not automatically configure CMSSW threads.
For HIP, use an explicit writable XRootD destination; bare `/store/` output
paths currently target CERN. The destination directory must already exist
when using a `root://` URL.

For MiniAOD using FlatTables producers to convert the PAT collections directly to Picos. It is exactly the same as Nano just with reduced info and possibiliy to add more info of course.

AOD and RECO can be converted directly
into the same Pico/FlatTable style used by the MiniAOD workflow.

Separates high-level and low-level objects:

```text
MiniAOD PAT objects ---------------------------> existing Pico tables

AOD/RECO reco objects e.g. jets/muons/electrons
            |
            +--> minimal PAT compatibility ----> existing Pico tables

AOD/RECO native reconstruction objects
            |
            +--> dedicated native producers ---> Pico FlatTables
```

The PAT compatibility layer is intentionally small. It does **not** attempt to
reproduce MiniAOD and does not run PNet, b tagging, flavour matching, trigger
matching, mini-isolation, or electron VID.

## Files
- `python/workflows/` contains the config files for the different tiers to pico NTuples production.
- Table configurations under `python/tables/`

- `python/tables/event_cff.py`: adds configurable PU/PV sources so AOD/RECO MC
  uses `addPileupInfo` and `offlinePrimaryVertices`, while MiniAOD defaults are
  unchanged.
- `python/tables/electrons_cff.py`: adds `includeIDs=True`. MiniAOD behaviour is
  unchanged; AOD/RECO can use the same table builder with `includeIDs=False`
  because the minimal PAT layer does not run VID.

## What a Pico records about itself

Every workflow puts `picoMetadata(process)` (`python/tables/metadata_cff.py`)
at the end of its Path. It makes the `nanoMetadata` module
(`PicoMetadataProducer`), whose strings `NanoAODOutputModule` writes as
`TObjString`s at the top of the file:

| string | content |
|---|---|
| `tag` | `Reco2Pico` |
| `picoCommand` | JSON: configuration path (relative to `$CMSSW_BASE/src`), SHA-1 of its contents, arguments, release |
| `picoProvenance` | JSON: the module writing each table (and its extensions), and for each module behind the tables the products it read in the job |
| `bookkeepingSchema` | only with the MC bookkeeping, see `tables/bookkeeping_cff.py` |

```python
import ROOT, json
f = ROOT.TFile.Open("pico.root")
prov = json.loads(str(f.Get("picoProvenance").GetString()))
prov["tables"]["Jet"]      # [{"module": "picoJetMCTable", "extension": true, ...}, {"module": "picoJetTable", ...}]
prov["modules"]["picoEBRecHitTable"]   # ["EcalRecHitsSorted_reducedEcalRecHitsEB__RECO"]
```

`navigator/navigator.py --pico pico.root` turns both strings into a page that
traces every branch to its definition, with no other input (see
`navigator/README.md`). The provenance is about 5 kB. It is frozen at the end
of the job's first run, so tables first written after that run are not
listed. `haddnano.py` keeps the strings of the first input file.

## Supported table groups

| group | AOD | RECO | source / notes |
|---|---:|---:|---|
| `event` | yes | yes | rho; PU table on MC |
| `muons` | yes | yes | `muons -> picoPatMuons -> Muon` |
| `electrons` | yes | yes | `gedGsfElectrons -> picoPatElectrons -> Electron` |
| `jets` | yes | yes | `ak4PFJetsPuppi -> picoPatJets -> Jet` |
| `pfcands` | yes | yes | native `particleFlow` |
| `tracks` | yes | yes | native `generalTracks` |
| `vertices` | yes | yes | native `offlinePrimaryVertices` |
| `pfclusters` | no* | yes | native PFCluster collections; standard AOD does not keep them |
| `rechits` | yes | yes | reduced AOD RecHits, fuller RECO RecHits; `fullEcalRecHits=True` (RECO) takes every ECAL rechit instead of the reduced collections |
| `pfblocks` | no | yes | native `particleFlowBlock`: `PFBlockElem`, `PFBlockLink`, `PFCandElem` (candidate -> element links); see "PF block tables" below |
| `genparts` | MC | MC | `GenPart` (pruned `genParticles` + all status 1), `GenJet` (anti-kt 0.4, no neutrinos, re-clustered in the job), `GenJetConst` |
| `simcalo` | no | MC | `SimCalo` (calorimeter deposits from the sim hits per calorimeter-entrance particle), `SimCaloCell` (the cells), `SimPFCand` (ideal PF), `SimCaloJet`, `SimCaloCellJet`, `SimPFJet` and their GenJet matches; needs the calorimeter sim hits kept in RECO and the `sim` group |
| `recojets` | no | MC | `PFCandTruth`/`PFCandSim` (PF candidates attributed to simulated particles), `PFJet`/`PFJetCHS`/`PFJetPuppi` re-clustered raw jets with constituents and ancestry GenJet matches; needs `pfcands`, `sim` and the calorimeter sim hits. With `pileupTruth=<label>` (classically mixed samples, see "Pile-up truth" below) `simcalo` and `recojets` add the pile-up deposits, `PFCandTruth_puFraction` and the jets with pile-up |
| `calodigis` | no | RECO + RAW | `EBDigi`, `EEDigi`, `HBHEDigi`: the ADC samples of every calorimeter cell above `digiMinAmplitude` [GeV], each sample also on the rechit energy scale; unpacked from the RAW data, so the RAW file must be the secondary input of the job (see "Calorimeter digis" below) |
| `sim` | MC* | MC | `SimTrack`/`SimVertex` (`g4SimHits`), `SimJet` (anti-kt 0.4 of the SimTracks), `SimGenJetMatch` (ancestry-based SimJet to GenJet scores, see below), `TP` (`mix:MergedTrackTruth`), `TrackTPLink` (track <-> TP association, `tpAssociation=chi2|hits|none`); needs `genparts` and a RECO that kept the sim truth (see `samples_workflows/run3_rawsim/`) |

`*` A custom AOD that explicitly keeps PFCluster collections can be supported
by changing the guard/source configuration; `sim` on AOD needs SimTracks,
TrackingParticles and DigiSimLinks kept in the file as well.

## Installation into the current repository

Copy the supplied files into the matching paths of your existing checkout.
The supplied `plugins/BuildFile.xml` is the current Reco2Pico BuildFile with the
extra DataFormats dependencies merged in.

## MiniAOD Example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  inputFiles=/store/.../MINIAODSIM/...root \
  maxEvents=100 \
  output=pico_aod.root \
  tables=event,muons,electrons,jets,pfcands,vertices
```

## AOD example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/AOD_to_pico_cfg.py \
  inputFiles=/store/.../AODSIM/...root \
  maxEvents=100 \
  output=pico_aod.root \
  tables=event,muons,electrons,jets,pfcands,tracks,vertices
```

For data you can normally let `isMC=auto` infer the type from `/store/data/`.
For local files use an explicit `isMC=true` or `isMC=false`.

## RECO example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=/store/.../RECO/...root \
  maxEvents=100 \
  output=pico_reco.root \
  tables=event,pfcands,tracks,vertices,pfclusters
```

or e.g. to inspect calorimeter RecHits:

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=/store/.../RECO/...root \
  maxEvents=10 \
  output=pico_rechits.root \
  tables=pfcands,tracks,vertices,pfclusters,rechits \
  recHitMinAbsEnergy=0.1
```

Note that RecHit tables can be large.

For a RECO produced from GEN-SIM-RAW with the sim truth kept (the chain in
`python/samples_workflows/run3_rawsim/`), the full truth and PF-structure content is:

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=file:step1.root isMC=true era=Run3_2025 globalTag=150X_mcRun3_2026_realistic_v4 \
  tables=event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim \
  output=pico_rawsim.root
```

## Sim jets and the SimJet to GenJet matching (`sim`)

### What a SimJet is

`SimJet` is a truth jet one step closer to the detector than `GenJet`: anti-kt
0.4 (same algorithm and radius as `ak4GenJetsNoNu`) run on the Geant4
`SimTrack`s of the signal event instead of the generator particles. The
constituents are therefore the particles *after* the decays and conversions
Geant4 simulated in the detector (K0S, Lambda, pi/K decays in flight with their
neutrinos lost, photon conversions, ...). Nothing reconstructed enters it.

Which SimTracks are clustered is set by `simJetSelection`:

| selection | constituents | momentum used |
|---|---|---|
| `entrance` (default) | the **calorimeter-entrance particles**: the cut through the stored Geant4 tree at the tracker/calorimeter boundary (next paragraph). Everything that decayed, converted or was absorbed in the tracker is replaced by its daughters or lost; everything born inside the calorimeter belongs to the particle that entered. | `momentum=production` (`SimJet`): the production momentum, with the energy of entrance daughters taken out; `momentum=boundary` (`SimBoundaryJet`): the momentum at the crossing where Geant4 recorded it (after the energy loss and the bending in the tracker), the production one otherwise |
| `leaves` | the terminal particles of the stored Geant4 tree: SimTracks without stored daughters, plus SimTracks whose stored daughters carry less than half of their energy (`SimTrack_dauEnergyFrac < 0.5`: delta rays, bremsstrahlung; the track itself continues) | at production |
| `boundary` | the same terminal particles | at the boundary crossing where recorded |
| `primaries` | generator particles only; reproduces `GenJet` up to the neutrino treatment | at production |

Neutrinos are always dropped. `SimTrack_simJetIdx` gives the jet of every
constituent; `SimJet_nConstituents` counts them.

### The calorimeter-entrance particles

The physical picture is one truth stage after the generator: the generator
particles are propagated by Geant4 through the tracker, where they decay,
convert, interact, lose energy and bend, and the particles that arrive at the
calorimeter face are the ones every later step sees. `SimJet` clusters their
production four-momenta (the particle list), `SimBoundaryJet` their momenta
at the face (the material and the bending on top), `SimCaloJet` the energy
they deposited, `SimPFJet` their momenta (charged, trackable) or deposits (the
rest).

Who they are is read off three facts of the Geant4 bookkeeping
(`SimG4Core/Notification/MCTruthUtil`, `SimG4CMS/Calo/CaloTrkProcessing`,
`CaloSD`):

* every stored secondary (a decay or conversion product of a primary, the
  only secondaries Geant4 keeps as SimTracks) gets its own "id on the
  calorimeter surface" at creation, wherever it is born; the unstored
  secondaries inherit the id of their mother;
* the boundary-crossing flag (`SimTrack_crossedBoundary`, with the position
  and momentum at the crossing) is set only for a track whose id on the
  surface is still zero when it steps into a calorimeter volume: primaries
  and unstored chains get it, a stored secondary born in the tracker never
  does, although it enters the calorimeter like any other particle;
* every calorimeter sim hit carries the id on the surface of the particle
  that deposited it, so the hits of a stored daughter born inside the
  calorimeter reference the daughter, not the particle that entered;
* at the end of the event the hits of a particle that was not saved as a
  SimTrack are re-keyed to its nearest saved ancestor, so a saved photon that
  converted in the tracker, or a saved pi0, can own the hits of unsaved
  descendants, while a saved secondary that inherited its mother's id (a
  bremsstrahlung photon, a delta ray, a continuation entry of the same
  particle) owns nothing: its hits are the mother's.

`PicoCaloEntranceProducer` therefore flags, top-down through the tree with an
entrance ancestor always winning, a SimTrack as an entrance particle when it
crossed the boundary, or when it was born inside the tracker volume
(r < 123 cm, |z| < 293 cm, where Geant4 records the crossings) and reaches
the calorimeter: it owns sim hits itself, or a chain of daughters born
outside the tracker does. A track born inside the calorimeter belongs to the
entrance particle of its parent; a track born inside the tracker is judged on
its own, so a bremsstrahlung photon or a delta ray that an entrance particle
emitted before the face is a separate entrance particle if it reaches the
calorimeter. Two momenta go with every entrance particle: the production
momentum, with the entrance energy of its tracker-born subtree taken out (its
tracker-born daughters that are entrance particles themselves, and the
entrance particles below a tracker-born daughter that is not one: a product
that decayed before the face, or the continuation entries Geant4 writes for
an electron after each bremsstrahlung), as an energy balance along the
production direction, so that a radiated photon counted on its own is not
counted twice (`SimTrack_entrancePt`, `SimTrack_entranceE`); and the momentum
at the face,
the one Geant4 recorded at the crossing, or the production one when the
crossing was not recorded (`SimTrack_facePt`, `SimTrack_faceE`). Nucleons and
nuclei born at a hadronic interaction vertex were knocked out of the tracker
material and carry a rest mass that never entered, so they count with their
kinetic energy (a 7.5 GeV pion interacting in the tracker otherwise comes out
as 10.9 GeV of products). With this bookkeeping the entrance energy of the
descendants of a generator particle sums to 0.99 of its energy in the local
test (1.02 before the subtree rule, with 142 of 3151 particles over-counted
by more than 5%). The examples:

* a photon converting in the tracker: the photon is before the cut, the two
  electrons are entrance particles with their own momenta at the face and
  their own deposits; converting in the last centimetres before the crystals
  or inside them, the photon is the entrance particle and the electrons'
  hits are merged into it;
* a pi+ decaying in flight in the tracker: the muon is the entrance
  particle, the neutrino is dropped; decaying inside HCAL: the pion is, and
  the muon's hits count with it;
* a K0S decaying inside ECAL: the K0S crossed the boundary and is the
  entrance particle, the two pions (stored, born in the crystals, owning the
  hits) are merged into it;
* a muon knocking out delta rays in the muon system: the muon crossed, the
  delta electrons are born outside the tracker and belong to it;
* a stored pion from a K0S decay in the tracker that reaches HCAL: no
  crossing flag (second bullet above), but it owns hits, so it is an entrance
  particle; its momentum at the face is not recorded, so the production one
  is used for both jets;
* a pion interacting in the tracker material: the stored products that own
  their hits (a leading pion, a pi0 through its photons) are entrance
  particles; the pion itself is one too if hits of unsaved products were
  re-keyed to it, with the energy its entrance daughters took removed.

In the 600-event check on the Run-3 DY sample, 5% of the deposited energy
sat on such flagless stored secondaries, 7% on daughters born inside the
calorimeter and 4% on particles that the earlier "terminal" rule (daughters
carrying less than half of the energy) excluded from the ideal PF list; all
three are now bookkept to the particle that entered.

`SimTrack_isEntrance`, `SimTrack_entranceIdx` (the entrance particle every
track belongs to) and `SimTrack_ownsCaloHits` expose the flags. The `leaves`
and `boundary` selections are kept for reference: `leaves` needed the
energy clause because 6 of the 10 Z muons of the first test events had
stored delta-ray daughters and would otherwise not have been clustered; the
entrance rule has no such clause.

### Matching SimJet to GenJet without geometry

At low pT the magnetic field shifts charged constituents in phi and decays in
flight move energy around, so a deltaR match is ambiguous exactly where the
response is interesting. The `SimGenJetMatch` table therefore matches through
ancestry, in the spirit of the HGCAL trackster to sim-trackster scores:

* every SimTrack descends from exactly one generator particle (the stored
  decay tree, `SimTrack_parentIdx`, ends at a generator primary);
* every generator particle is a constituent of at most one GenJet
  (`GenJetConst`; the gen jets are re-clustered in the job from `genParticles`
  so that their constituents are known).

For every (SimJet s, GenJet g) pair that shares energy, one row with

| column | meaning |
|---|---|
| `sharedEnergy` | energy (as clustered) of the constituents of s whose generator ancestor is a constituent of g |
| `simFraction` | `sharedEnergy / E(s)`: how much of the SimJet comes from this GenJet (purity of s with respect to g) |
| `genFraction` | sum over the constituents p of g of `E(p) * f_s(p) / E(g)`, with `f_s(p)` the fraction of the clustered descendant energy of p that ended up in s: how much of the GenJet is found in this SimJet (efficiency of g into s) |
| `nShared` | number of SimJet constituents descending from g |
| `ptRatio` | `pt(s) / pt(g)`, the response of the pair |
| `dR` | deltaR of the two axes, for reference only |
| `bestForSim`, `bestForGen` | the pair with the largest `sharedEnergy` for s, the largest `genFraction` for g |

A matched pair for a response measurement is `bestForSim && bestForGen` with
`simFraction > 0.5 && genFraction > 0.5`; the thresholds are yours to tune
since both fractions are stored. In the 5-event local test 27 of 34 gen jets
above 5 GeV have such a partner, the two Z muons match with fractions of 1 and
ratio 1.00, and hadronic jets at 20 GeV show ratios of 0.8 to 0.9 (decay
neutrinos and out-of-cone decay products), which is the effect this is meant to
measure.

`GenJetConst` (`genJetIdx`, `genPartIdx`, `energy`) lists the gen-jet
constituents, so the same bookkeeping can be redone with other thresholds or
other energy weights offline.

### What `ptRatio` measures, and what it does not

SimJet constituents are SimTrack four-momenta, i.e. particle kinematics.
Geant4 enters only through what it did to the particle list. `ptRatio` of a
matched pair is therefore the response due to:

* decays in flight (pi, K, K0S, Lambda, ...): the neutrinos are lost and the
  charged daughters can leave the cone;
* photon conversions and the other stored secondaries (the energy stays, only
  its carriers change);
* the energy lost in the tracker material and the bending of the charged
  constituents in the field, since the momenta are taken at the boundary
  crossing (`leaves` uses the production momenta instead).

It does **not** contain the calorimeter response of Geant4: the hadron
response below one from non-compensation and invisible energy, shower leakage,
energy lost in dead material, thresholds and sampling. SimJet is "what entered
the detector", not "what the detector saw". The 0.8 to 0.9 ratios of the
20 to 40 GeV hadronic jets in the local test are decays only, and are the
baseline every reconstruction-level response has to be compared against.

The full ladder, from the generator to the reconstruction, is then

| step | object | adds |
|---|---|---|
| 1 | `GenJet` | generator particles (no neutrinos) |
| 2 | `SimJet` | the calorimeter-entrance particles with their production momenta: decays in flight, conversions, interactions in the tracker |
| 3 | `SimBoundaryJet` | the same particles with their momentum at the calorimeter face: energy loss in the tracker material and bending (soft charged particles leave the cone) |
| 4 | `SimCaloJet` (`simcalo`) | the Geant4 calorimeter response: jets of the deposits per entrance particle (`SimCalo`), everything (charged particles too) taken from the calorimeter; `SimCaloCellJet` clusters the same deposits as cells (`SimCaloCell`), i.e. with the calorimeter geometry instead of one direction per particle |
| 5 | `SimPFJet` (`simcalo`) | an ideal particle flow: charged entrance particles inside the tracker acceptance from their momentum, the rest from their deposit (`SimPFCand`) |
| 6 | `PFJet`, `PFJetCHS`, `PFJetPuppi` (`recojets`) | the reconstruction: clustering, thresholds, calibration, the PF algorithm, and the pile-up with its mitigation (none, CHS, Puppi) |

Every jet collection, sim-level and reconstructed, is matched to `GenJet` by
the same ancestry scores (`SimGenJetMatch`, `SimBoundaryGenJetMatch`,
`SimCaloGenJetMatch`, `SimCaloCellGenJetMatch`, `SimPFGenJetMatch`,
`PFJetGenMatch`, `PFJetCHSGenMatch`, `PFJetPuppiGenMatch`), so the response
can be followed step by step for the same gen jet, and the difference between
two steps isolates one effect: 2 vs 1 the particle list after the tracker,
3 vs 2 the material and the bending, 4 vs 3 the calorimeter, 5 vs 4 what
perfect tracking recovers, 6 vs 5 the reconstruction and the pile-up.

### Per-particle calorimeter deposits (`simcalo`)

The calorimeter sim hits of the GEN-SIM-RAW (`EcalHitsEB/EE/ES`, `HcalHits`)
carry the deposited energy and the Geant4 "id on the calorimeter surface"
(CaloSD): the particle that entered the calorimeter, or a stored daughter born
inside it. Every hit is assigned to the calorimeter-entrance particle of that
id (the id itself or its entrance ancestor, `SimTrack_entranceIdx`), so each
deposit is counted exactly once with the particle that entered. No clustering
is needed: the deposits are summed per entrance particle into `SimCalo`, one
row per particle with a deposit:

* `ecalEnergy` (EB+EE), `esEnergy`, `hcalEnergy` (HB+HE), `hoEnergy`,
  `hfEnergy` and their sum `energy`, all GeV-equivalent: the HCAL hits are
  relabelled from the Geant4 test numbering and scaled with the digitiser's
  sampling factors (`hcalSimParameters`, era modifiers applied), the HF
  photoelectrons with the HF factors, so the numbers are what the digitiser
  would call GeV;
* `eta`/`phi`: the energy-weighted direction of the cells, `pt` along it;
* `boundaryE`: the particle's energy when it entered, and
  `response = energy / boundaryE`, the single-particle calorimeter response;
* `nOwners`: how many SimTracks' hits were merged into the row (itself and
  its stored daughters born in the calorimeter);
* `simTrackIdx` and `simCaloJetIdx`.

Cells are summed over all particles first; an optional per-cell threshold
(`ecalCellThreshold`, `hcalCellThreshold`, default 0) is applied to the cell
total, as a rechit threshold would be, and the cell energy is then shared
between the contributing particles in proportion to their deposits. The
threshold effect can thus be switched on separately from the response itself.
The sim hits exist for the signal event only, so these deposits are pile-up
free.

`SimCaloCell` is the same energy seen as cells: one row per cell above
threshold with its total deposit over all particles, its DetId, subdetector
and centre, and the number of entrance particles sharing it. It is the
signal-only, noiseless, cell-level truth of what the calorimeter saw, before
any tower or cluster building: finer than a CaloTower (every crystal and every
HCAL depth is its own row), without the pile-up, noise, calibration and
zero-suppression of the reconstruction, and with the truth decomposition
attached. `SimCaloCellJet`
is anti-kt 0.4 of the cells; its gen-jet match (`SimCaloCellGenJetMatch`)
splits every cell between the entrance particles in proportion to their
deposits, so the ancestry scores are as exact as for the per-particle jets.
`SimCaloJet` and `SimCaloCellJet` carry the same energy and differ only in
the geometry: one direction per particle (the energy-weighted direction of
its cells) against the cells themselves, so the pair separates the energy
response of the calorimeter from the treatment of the shower geometry
(splash-out of wide showers, cells shared between jets).

`SimPFCand` is the ideal particle-flow list, built from the same
calorimeter-entrance particles as `SimJet` (no neutrinos): a particle that is
charged, produced inside the tracker volume (r < 123 cm, |z| < 293 cm), inside
the acceptance (`simPFChargedMaxAbsEta`, 2.5) and above `simPFChargedMinPt`
(0.5 GeV) enters with its production momentum as an entrance particle, i.e.
the `SimJet` one (`kind` 1, "perfect tracking");
every other particle enters with its deposit (`kind` 2 neutral, 3 charged but
not trackable) or not at all if it left none. `SimCaloJet` and `SimPFJet` are
anti-kt 0.4 of `SimCalo` and `SimPFCand`.

Limits of the ideal PF: a pion decaying inside the tracker contributes its
muon's momentum rather than its own track, and nothing is subtracted for
charged particles, since their deposit is not used.

Energy scale: on the classically mixed sample (`run3_mix`), where every
cell's deposit is known, the reconstructed cell energy over the in-time sim
deposit is 1.00 in EB, 1.05 in EE and HO, and 0.74 / 0.75 in HB / HE (the PF
cluster calibration brings the hadrons back up), so the digitiser
GeV-equivalent is the rechit scale for the ECAL and 1.35 times it for the
HCAL. The HF conversion from shower-library photoelectrons misses the gain:
rechits are 14.2 (depth 1) and 12.8 (depth 2) times the digitiser number,
with a broad spread (16 to 84%: 10.6 to 18.1). `caloSimHitParameters` applies
these as `rechitScale` (`SIM_SCALE`: the digitiser scale with the HF gain, for
the sim-level objects; `RECHIT_SCALE`: the rechit scale, for the attribution
of reconstructed candidates, whose cap has to be on that scale). The HF
numbers are therefore GeV-equivalent since this calibration, but with the
resolution of the shower library.

What the Run-3 DY production shows (barrel, hadronic gen jets of 30 to
40 GeV, shared-energy response, `docs/TrueJES.md` section 4): `SimJet` 0.92,
`SimBoundaryJet` 0.73, `SimCaloJet` 0.74, `SimCaloCellJet` 0.73, `SimPFJet`
0.88, the signal part of the reconstructed PF jet 0.80. The particle list
after the tracker costs 8%, the bending and the material at the face another
19%, the calorimeter response relative to the face is close to one at this
pT, perfect tracking brings most of it back, and the reconstruction takes
8% more. The single-particle `response` (deposit over energy at the face)
is close to 1 for photons and kaons, about 0.75 for charged pions and 0.15
for muons in the first test events. These are the numbers the reconstructed
PF jets have to be compared against, at the same gen jet through the match
tables.

### Reconstruction-level truth (`recojets`)

To put the reconstructed jets on the same ladder, every PF candidate is first
attributed to the simulated particles of the signal event (`PFCandTruth`, one
row per `PFCand` row, and the (candidate, particle) shares in `PFCandSim`):

* a candidate with a track takes the TrackingParticle associated to that track
  (the `sim` group's track association, best quality) and gives its whole
  energy to that particle (`method` 1);
* any other candidate is attributed through its PF clusters, cell by cell: the
  reconstructed cell energy (rechit times cluster fraction) is shared among the
  signal particles in proportion to their sim-hit deposits in the cell, capped
  by the GeV-equivalent sim energy of the cell, so that pile-up energy on top
  of a small signal deposit stays unattributed (`method` 2);
* what remains is unattributed: pile-up, noise and fakes. `signalFraction` is
  the attributed share of the candidate energy; `simTrackIdx` the dominant
  particle.

The jets are re-clustered in the job with the standard definitions (anti-kt
0.4 of `particleFlow`; CHS on `pfNoPileUpJME`; Puppi with the `puppi` weights),
raw without JEC, because the stored CHS and Puppi jets do not keep usable
constituent references. `<Jet>Const` lists the constituents with their
clustering weight, `area` is the jet catchment area, and for `PFJetPuppi` the
GlobalTag AK4PFPuppi corrections are evaluated and stored as factors on the raw
jet (`jecL1`, `jecL1L2L3`; the jets themselves stay raw, so any level can be
rebuilt offline). `<Jet>GenMatch` carries the ancestry scores of
`SimGenJetMatch` (`recoFraction` plays the role of `simFraction`) plus
`signalPtRatio`: the pt of the signal-attributed part of the jet over the
GenJet pt, i.e. the response with the pile-up removed by attribution rather
than by any algorithm. The difference between `ptRatio` and `signalPtRatio` is
the pile-up contribution of that jet; the difference between `signalPtRatio`
and the `SimPFJet` ratio is what the reconstruction itself did to the signal.

On the 5-event test (2026 pile-up conditions) the central gen jets above
8 GeV read, as `ptRatio` [`signalPtRatio`]: PF 1.3 to 3.0 [0.9 to 1.05], CHS
1.1 to 1.7 [0.9 to 1.0], Puppi 1.0 to 1.4 [0.9 to 1.0]. Pile-up therefore
does not need to be matched between samples for the signal response: the
attribution takes it out jet by jet, and the raw ratios quantify what each
mitigation leaves in.

### Pile-up truth of classically mixed samples (`pileupTruth`)

The premixed Run-3 samples carry the signal truth only: the pile-up is a
pre-digitised library whose particles and sim hits are gone. The
`samples_workflows/run3_mix` chain mixes the signal GEN-SIM with minimum-bias
GEN-SIM events the classical way in the DIGI step, where
`PicoMixedTruthProducer` (label `picoMixedTruth`) reads the transient
CrossingFrames of the mixing module and writes, as ordinary collections, the
SimTracks, SimVertices and calorimeter sim hits of the in-time pile-up
interactions (each with its `EncodedEventId`) and the out-of-time deposits
summed per cell and bunch crossing. With `pileupTruth=picoMixedTruth` the
`simcalo` and `recojets` groups use them:

* `SimCaloCell` gains `puEnergy` (in-time pile-up deposit of the cell),
  `ootEnergy` (out-of-time, all crossings) and `nPU` (interactions with a
  deposit in the cell): every cell is signal + known pile-up + the rest;
* the pile-up particles get their own calorimeter-entrance list
  (`picoCaloEntrancePU`, the same rule keyed by interaction and track id) and
  three jets with pile-up are clustered and matched to the gen jets through
  the signal ancestry: `SimCaloCellPUJet` (cells with signal + in-time
  pile-up, the calorimeter truth with pile-up and no noise or thresholds),
  `SimPFPUJet` (the ideal PF of signal + pile-up particles: charged trackable
  from momentum, the rest from deposits, `kind` 11/12/13 for the pile-up
  entries) and `SimPFPUCHSJet` (the same without the trackable charged
  pile-up: a perfect charged-hadron subtraction, leaving the neutral and
  untrackable pile-up);
* `PFCandTruth_puFraction`: the share of every PF candidate attributed to
  in-time pile-up particles, through the track of a pile-up TrackingParticle
  or the pile-up share of the cluster cells (the cap of the attribution is
  then the full in-time sim energy of the cell, signal plus pile-up), so that
  `1 - signalFraction - puFraction` is what neither is: noise, out-of-time
  pile-up and the calibration residual.

The offsets of the TrueJES analysis are thereby split into the true in-time
pile-up by candidate type and the residual, and the raw reconstructed jets can
be compared with their ideal counterparts with pile-up.

## Calorimeter digis (`calodigis`)

The RECO files carry the rechits, not the samples the pulse fits were made
from (RECO keeps only the ECAL digis around selected objects and no HBHE
digis). The `calodigis` group unpacks the ECAL and HCAL digis from the RAW
data in the Pico job (`picoEcalDigis`, `picoHcalDigis` on `rawDataCollector`)
and writes one row per cell whose largest pedestal-subtracted sample exceeds
`digiMinAmplitude` (0.1 GeV by default):

| table | columns |
|---|---|
| `EBDigi`, `EEDigi` | `rawId`, `ieta`/`iphi` or `ix`/`iy`/`zside`, `adc0..9` (ADC code), `gain0..9` (MGPA gain id: 1 x12, 2 x6, 3 x1, 0 saturated), `e0..9` = (adc - pedestal of the gain) x gain ratio to gain 12 x ADCToGeV x intercalibration x laser correction, i.e. the sample on the rechit scale as multifit sees it; `pedestal` (gain 12), `gevPerAdc`, `laser`, `saturated` |
| `HBHEDigi` | `rawId`, `subdet`, `ieta`, `iphi`, `depth`, `soi` (the sample of the in-time crossing), `nSamples` (8 or 10), `adc0..9`, `tdc0..9`, `capid0..9`, `fc0..9` (the charge of the ADC code from the QIE coder), `e0..9` = (fc - pedestal of the capacitor) x response-corrected gain, the sample on the rechit scale as MAHI sees it; `pedestal`, `gain` of capacitor 0 |

The RAW file is given as the secondary input (the two-file solution), for
instance the `step0.root` of the `run3_mix` chain next to its `step1.root`:

```bash
cmsRun python/workflows/RECO_to_pico_cfg.py inputFiles=file:step1.root secondaryInputFiles=file:step0.root \
  tables=event,...,rechits,calodigis fullEcalRecHits=True digiMinAmplitude=0.1 ...
```

With ten samples of a few hundred ECAL and seven thousand HCAL cells per
event the tables are the largest of the Pico, hence the threshold and the
separate small samples (`analysis/CaloPulses/README.md`).

## PF block tables (`pfblocks`)

The `pfblocks` group writes the particle-flow block structure of RECO as three
tables that answer three different questions. Keep them apart:

| table | question it answers | one row per |
|---|---|---|
| `PFBlockElem` | **What elements exist?** The inventory: every `reco::PFBlockElement` of every block, with its type and a pointer to the physical object (`Track`, `PFCluster<X>` row). Says nothing about relations between elements. | element |
| `PFBlockLink` | **What did PF find geometrically connected?** The links of `PFBlock::linkData()`: pairs of elements that passed a linker test, with the linking distance. This is the *input* of the PF algorithm, not its decision. | linked pair |
| `PFCandElem` | **What did PF decide to use?** The elements each final `PFCand` is built from (`reco::PFCandidate::elementsInBlocks()`). | (candidate, element) pair |

`PFBlockLink` and `PFCandElem` both point into `PFBlockElem` through element
rows (`elemRow1`/`elemRow2` and `elemRow`), and `PFBlockElem` resolves each row
to the detector object. The physics usually sits in the difference between the
last two tables: a track linked to several clusters whose candidate kept only
one, or a cluster linked to a track that was nevertheless left as a neutral
candidate.

### How the links are made

The PF block producer runs one linker per element-pair type over all elements
of the event. Each linker applies a geometric test and returns a distance, or
-1 when the pair fails; only passing pairs are stored. A block is a connected
component of that graph. Most blocks are single unlinked elements; the
interesting ones hold tens to hundreds of elements.

| pair | `distance` | notes |
|---|---|---|
| TRACK-ECAL | eta-phi distance between the track extrapolated to the ECAL entrance and the cluster position | the track must enter the cluster's crystal envelope |
| TRACK-HCAL | eta-phi distance at the HCAL entrance | clusters are wide, so values up to ~1.5 are normal |
| TRACK-HO, GSF-ECAL, GSF-HCAL, BREM-ECAL | eta-phi distance of the (GSF/tangent) extrapolation to the cluster | |
| ECAL-HCAL, HCAL-HO, ECAL-ECAL | eta-phi distance between cluster positions | accepted only below 0.2 |
| ECAL-PS1 / ECAL-PS2 | eta-phi distance between the preshower and ECAL clusters | |
| HFEM-HFHAD | ~0 | the two HF clusters share a cell |
| GSF-BREM, GSF-TRACK, SC-ECAL | 0.001 | constant placeholder: "same object", no geometry |
| TRACK-TRACK | 1.0 | constant placeholder: both tracks share a displaced vertex, conversion or V0 |

`PFBlockLink_test` is the link-test bit mask of the release; it is 1 for every
row and carries no information. The KDTree linkers pre-select nearest
neighbours, so a missing link means "never linked", not "tested and rejected".
Links exist only inside a block.

### Column reference

`PFBlockElem`: `blockIdx`, `elemIdx` (position in the block), `type`
(1 TRACK, 2 PS1, 3 PS2, 4 ECAL, 5 HCAL, 6 GSF, 7 BREM, 8 HFEM, 9 HFHAD, 10 SC,
11 HO, 12 HGCAL), `pt`/`eta`/`phi`/`energy` of the linked object, `trackIdx`
(row of `Track`), `clusterTable` (1 ECAL, 2 HCAL, 3 HO, 4 HF, 5 PS) and
`clusterIdx` (row of that `PFCluster<X>` table), raw keys (`trackKey`,
`clusterKey`, `gsfTrackKey`, `muonKey`, `superClusterKey`), `trackTypeBits`
(bit 1 from displaced vertex, 2 to displaced vertex, 3 from conversion, 4 muon,
5 from V0), `linkedToDisplacedVertex`, `hasConversion`, `hasV0`,
`ecalEntranceEta`/`ecalEntrancePhi` (track extrapolation), `bremDeltaP`,
`time`/`timeError`, `candIdx` (first `PFCand` using the element, -1 if unused)
and `nCands`.

`PFBlockLink`: `blockIdx`, `elem1`, `elem2` (positions in the block,
`elem1 < elem2`), `elemRow1`, `elemRow2` (rows of `PFBlockElem`), `distance`,
`test`.

`PFCandElem`: `candIdx` (row of `PFCand`), `blockIdx`, `elemIdx`, `elemRow`
(row of `PFBlockElem`), `type`.

Row indices follow the thresholds of the other tables (`pfCandMinPt`,
`trackMinPt`, `pfClusterMinEnergy`): a filtered object gives -1 while the raw
key is always filled.

### Example: what a charged hadron could have used

1. `PFCandElem` rows with the candidate's `candIdx`: the elements it is made of;
   the `type == 1` row is its track element, `elemRow` its row in `PFBlockElem`.
2. `PFBlockLink` rows whose `elemRow1` or `elemRow2` equals that row: every
   cluster PF found connected to the track, with the distance.
3. Clusters in step 2 that are not in step 1 were assigned to a neighbouring
   candidate or left as neutral candidates (`PFBlockElem_candIdx` of that
   cluster tells which); compare their energy with the track momentum to see
   why.

The reverse works for a photon or neutral hadron: the links of its cluster
element list the tracks that were in reach when it was declared neutral.

## Filtering and indices conventions

`PFCand_trackIdx` points to a row of the Pico `Track` table, not blindly to the
original `reco::TrackRef::key()`. The producer remaps the index when
`trackMinPt` is non-zero.

Example:

```bash
trackMinPt=0.5 pfCandMinPt=0.2
```

still gives a valid `PFCand_trackIdx` for tracks retained in the Track table;
tracks removed by the threshold receive `trackIdx = -1`.

`Track_pvIdx` points to the row of the native `Vertex` table with the largest
vertex-fit weight for that track.
