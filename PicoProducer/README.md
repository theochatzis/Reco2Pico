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
| `rechits` | yes | yes | reduced AOD RecHits, fuller RECO RecHits |
| `pfblocks` | no | yes | native `particleFlowBlock`: `PFBlockElem`, `PFBlockLink`, `PFCandElem` (candidate -> element links); see "PF block tables" below |
| `genparts` | MC | MC | `GenPart` (pruned `genParticles` + all status 1), `GenJet` (anti-kt 0.4, no neutrinos, re-clustered in the job), `GenJetConst` |
| `simcalo` | no | MC | `SimCalo` (per-particle calorimeter deposits from the sim hits), `SimPFCand` (ideal PF), `SimCaloJet`, `SimPFJet` and their GenJet matches; needs the calorimeter sim hits kept in RECO and the `sim` group |
| `recojets` | no | MC | `PFCandTruth`/`PFCandSim` (PF candidates attributed to simulated particles), `PFJet`/`PFJetCHS`/`PFJetPuppi` re-clustered raw jets with constituents and ancestry GenJet matches; needs `pfcands`, `sim` and the calorimeter sim hits |
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
| `leaves` (default) | the terminal particles of the stored Geant4 tree: SimTracks without stored daughters, plus SimTracks whose stored daughters carry less than half of their energy (`SimTrack_dauEnergyFrac < 0.5`: delta rays, bremsstrahlung; the track itself continues). Decays and conversions replace the parent by its daughters. | at production |
| `boundary` | the same terminal particles | at the tracker/calorimeter boundary where Geant4 recorded the crossing (after the energy loss and bending in the tracker); particles born inside the calorimeter keep their production momentum |
| `primaries` | generator particles only; reproduces `GenJet` up to the neutrino treatment | at production |

Neutrinos are always dropped. `SimTrack_simJetIdx` gives the jet of every
constituent; `SimJet_nConstituents` counts them.

Why the "less than half of the energy" clause: Geant4 stores a daughter
SimTrack not only for decays and conversions but also for the occasional
secondary a continuing particle produces. In the local test, 6 of the 10 Z
muons had knocked out one to three delta-ray electrons of 10 to 400 MeV in the
muon system (vertices at a radius of 4 to 6 m, Geant4 process type 2,
ionisation). With a strict "no stored daughters" rule those muons were not
clustered at all, their 45 GeV gen jets had no sim partner, and the only
"match" of such a gen jet was a 5 GeV jet sharing a converted photon. With the
energy clause the muon (daughters carry 0.0 to 0.01 of its energy) is a
terminal particle again, the delta electrons are kept as constituents too, and
all ten muon jets match with fractions of 1. A pion decaying in flight, by
contrast, has daughters carrying its full energy (`dauEnergyFrac` ~ 1) and is
correctly replaced by its muon, the neutrino being dropped.

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
* with `simJetSelection=boundary`, in addition the energy lost in the tracker
  material and the bending of the charged constituents in the field.

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
| 2 | `SimJet`, `leaves` | decays in flight, conversions |
| 3 | `SimJet`, `boundary` | tracker material and bending (momentum at the calorimeter surface) |
| 4 | `SimCaloJet` (`simcalo`) | the Geant4 calorimeter response: jets of the per-particle deposits `SimCalo`, everything (charged particles too) taken from the calorimeter |
| 5 | `SimPFJet` (`simcalo`) | an ideal particle flow: charged particles inside the tracker acceptance from their momentum, the rest from their deposit (`SimPFCand`) |
| 6 | `PFJet`, `PFJetCHS`, `PFJetPuppi` (`recojets`) | the reconstruction: clustering, thresholds, calibration, the PF algorithm, and the pile-up with its mitigation (none, CHS, Puppi) |

Every jet collection, sim-level and reconstructed, is matched to `GenJet` by
the same ancestry scores (`SimGenJetMatch`, `SimCaloGenJetMatch`,
`SimPFGenJetMatch`, `PFJetGenMatch`, `PFJetCHSGenMatch`, `PFJetPuppiGenMatch`),
so the response can be followed step by step for the same gen jet, and the
difference between two steps isolates one effect: 2 vs 1 the decays, 4 vs 3
the calorimeter, 5 vs 4 what perfect tracking recovers, 6 vs 5 the
reconstruction and the pile-up.

### Per-particle calorimeter deposits (`simcalo`)

The calorimeter sim hits of the GEN-SIM-RAW (`EcalHitsEB/EE/ES`, `HcalHits`)
carry the deposited energy and the Geant4 id of the particle that *entered*
the calorimeter (CaloSD stores the id on the calorimeter surface), i.e. exactly
the `boundary` SimTracks. No clustering is needed: the deposits are summed per
particle into `SimCalo`, one row per particle with a deposit:

* `ecalEnergy` (EB+EE), `esEnergy`, `hcalEnergy` (HB+HE), `hoEnergy`,
  `hfEnergy` and their sum `energy`, all GeV-equivalent: the HCAL hits are
  relabelled from the Geant4 test numbering and scaled with the digitiser's
  sampling factors (`hcalSimParameters`, era modifiers applied), the HF
  photoelectrons with the HF factors, so the numbers are what the digitiser
  would call GeV;
* `eta`/`phi`: the energy-weighted direction of the cells, `pt` along it;
* `boundaryE`: the particle's energy when it entered, and
  `response = energy / boundaryE`, the single-particle calorimeter response;
* `simTrackIdx` and `simCaloJetIdx`.

Cells are summed over all particles first; an optional per-cell threshold
(`ecalCellThreshold`, `hcalCellThreshold`, default 0) is applied to the cell
total, as a rechit threshold would be, and the cell energy is then shared
between the contributing particles in proportion to their deposits. The
threshold effect can thus be switched on separately from the response itself.
The sim hits exist for the signal event only, so these deposits are pile-up
free.

`SimPFCand` is the ideal particle-flow list, built from the same terminal
particles as `SimJet` (no neutrinos): a particle that is charged, produced
inside the tracker volume (r < 110 cm, |z| < 280 cm), inside the acceptance
(`simPFChargedMaxAbsEta`, 2.5) and above `simPFChargedMinPt` (0.5 GeV) enters
with its production momentum (`kind` 1, "perfect tracking"); every other
particle enters with its deposit (`kind` 2 neutral, 3 charged but not
trackable) or not at all if it left none. `SimCaloJet` and `SimPFJet` are
anti-kt 0.4 of `SimCalo` and `SimPFCand`.

Why the terminal-particle rule and not Geant4's boundary flag: the flag
(`SimTrack_crossedBoundary`) is set when a track steps from the tracker volume
into the calorimeter volume, so particles born inside the calorimeter (pions
of a K0S decaying in ECAL, electrons of a conversion in the crystals) never
carry it although the sim hits reference them, and a hadron that interacts in
the tracker material carries it only if it survives; in the 5-event test 363
particles with deposits had no flag. The terminal rule covers both cases:
the daughters are terminal, the parent is not.

Limits of the ideal PF: a pion decaying inside the tracker contributes its
muon's momentum rather than its own track, and nothing is subtracted for
charged particles, since their deposit is not used.

Energy scale: the HB/HE/HO factors reproduce the digitiser's GeV scale; the
HF conversion (photoelectrons of the shower library times the HF factor) has
not been validated against reconstructed energies and comes out low (around
0.2 for hadrons in the test). `hfEnergy` is stored separately so that the HF
scale can be calibrated offline from `SimCalo` itself; for the tracker
acceptance this does not matter.

What the 5-event test shows (barrel, particles that crossed the boundary with
more than 5 GeV): the median single-particle calorimeter `response` is 0.96
for the photon and the kaons, 0.73 for charged pions and 0.15 for muons (the
MIP deposit). On the jet ladder, the 17 GeV gen jet of event 3 gives 0.89
(`SimJet`), 0.63 (`SimCaloJet`) and 0.85 (`SimPFJet`): the decays cost 11%,
the calorimeter another 26%, and perfect tracking brings 22% back. The 56 GeV
muon jet of event 2 reads 1.00, 0.11 and 1.00. These are the numbers the
reconstructed PF jets have to be compared against, at the same gen jet through
the match tables.

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
