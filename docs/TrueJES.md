# TrueJES: where the jet energy scale comes from

A jet energy scale measured on reconstructed jets mixes many effects: what
happened to the particles before they reached the detector, what the
calorimeter does to them, what tracking recovers, what the reconstruction
algorithms add or lose, and the pile-up. This study separates them by
building one jet collection per step on the same simulated events and
matching every step to the same generator jet without any geometric
criterion. It uses the Reco2Pico Picos of the `run3_rawsim` chain
(GEN-SIM-RAW re-reconstructed with the simulation truth kept) on the
Run3Winter26 `DYto2Mu-4Jets` sample (2026 pile-up conditions), and the
`analysis/TrueJES` package.

## 1. The ladder

| step | jet | definition | what the step adds |
|---|---|---|---|
| 1 | `GenJet` | anti-kt 0.4 of the generator particles, no neutrinos (`ak4GenJetsNoNu`), re-clustered in the Pico job | the reference |
| 2 | `SimJet` | anti-kt 0.4 of the Geant4 `SimTrack`s of the signal event: the terminal particles of the stored decay tree, no neutrinos, production momenta | decays in flight (pi, K, K0S, Lambda; neutrinos lost, daughters out of cone) and conversions |
| 3 | `SimJet`, `boundary` option | the same particles with the momentum Geant4 recorded when they entered the calorimeter | energy loss in the tracker material and the bending of charged particles |
| 4 | `SimCaloJet` | anti-kt 0.4 of the per-particle calorimeter deposits summed from the Geant4 sim hits (`SimCalo`), everything taken from the calorimeter | the calorimeter response: non-compensation, invisible energy, leakage, dead material |
| 5 | `SimPFJet` | anti-kt 0.4 of an ideal particle flow (`SimPFCand`): terminal charged particles produced in the tracker volume, within acceptance and above 0.5 GeV with their momentum, everything else with its deposit | what perfect tracking recovers |
| 6 | `PFJet`, `PFJetCHS`, `PFJetPuppi` | the reconstructed jets, re-clustered raw (no JEC) with the standard definitions | the reconstruction: thresholds, clustering, the PF algorithm, and the pile-up with no, CHS or Puppi mitigation |

Two choices in the definitions deserve a word.

**Terminal particles.** Geant4 stores a daughter SimTrack for decays and
conversions, but also for the occasional secondary of a particle that
continues (a delta-ray electron knocked out by a muon, a bremsstrahlung
photon). A particle is therefore terminal when its stored daughters carry
less than half of its energy; decays and conversions replace the parent by
its daughters, delta rays do not. Without this clause, 6 of the 10 Z muons of
the first test events were dropped from the sim jets because of delta rays in
the muon system. The same rule defines the ideal PF list, rather than Geant4's
boundary-crossing flag: that flag is set when a track steps from the tracker
volume into the calorimeter, so particles born inside the calorimeter (pions
of a K0S decaying in ECAL, conversion electrons in the crystals) never carry
it although the sim hits reference them.

**GeV-equivalent deposits.** The calorimeter sim hits carry the deposited
energy and the Geant4 id of the particle that entered the calorimeter, so
the deposits are summed per particle without any clustering. HCAL hits are
relabelled from the test numbering and scaled with the digitiser's sampling
factors, so the numbers are on the digitiser's GeV scale; the HF conversion
from shower-library photoelectrons is not validated and comes out low, which
does not matter inside the tracker acceptance.

## 2. Matching without geometry

At low pT the field shifts charged constituents in phi and decays in flight
move energy around, so a deltaR match is ambiguous exactly where the response
is interesting. Every SimTrack descends from one generator primary through
the stored decay tree, and every generator particle is a constituent of at
most one gen jet; a jet at any step is therefore matched to gen jets through
the ancestry of its constituents, in the spirit of the HGCAL trackster
scores. For a (jet j, gen jet g) pair:

* `sharedEnergy`: energy of the constituents of j descending from g;
* `simFraction` (or `recoFraction`) = sharedEnergy / E(j): purity of j;
* `genFraction`: share of the gen jet energy whose descendants, as clustered
  (or as reconstructed), ended up in j: efficiency of g into j.

For the reconstructed jets the constituents are PF candidates, first
attributed to simulated particles: charged candidates through the track to
TrackingParticle association, the others cell by cell through the sim-hit
shares of their cluster cells, capped by the simulated energy of the cell.
What is not attributed is pile-up, noise or fakes, and `signalPtRatio` is
the response of the attributed part alone.

A gen jet counts as matched at a step when the pair flagged best for it has
both fractions above 0.5. Gen jets within 0.4 of a generator muon above
10 GeV (the Z decay) are excluded.

## 3. Pile-up: attribution, not subtraction

Pile-up is not subtracted from the reconstructed jets and no pile-up
matching between samples is done. Instead every PF candidate is split into a
part that can be traced to a simulated particle of the hard-scatter event and
a remainder, and the "signal part" of a jet is the sum of the traced parts of
its constituents (`analysis/TrueJES/illustrations/pileup_attribution.pdf`).

**Per candidate** (`PFCandTruth`, with the individual shares in `PFCandSim`):

* A candidate with a track (charged hadrons, electrons, muons): the track is
  associated to a TrackingParticle by the chi2 associator, the TrackingParticle
  leads to its SimTrack, and the whole candidate energy is attributed to that
  particle. A track without an associated TrackingParticle gets nothing. The
  sample is premixed, so TrackingParticles exist for the hard-scatter event
  only, and every pile-up track falls in the "nothing" category automatically.
* A candidate without a track (photons, neutral hadrons, HF): through its PF
  clusters, cell by cell. The reconstructed energy of a cell is the rechit
  energy times the cluster fraction. The simulated deposit of every
  hard-scatter particle in that cell is known from the sim hits. The attributed
  energy of the cell is the smaller of the reconstructed energy and the total
  simulated signal energy of the cell, shared among the particles in proportion
  to their deposits; the rest stays unattributed. The sim hits, too, exist for
  the hard-scatter event only, so energy without a simulated counterpart is
  pile-up, noise or a fake.
* The attributed energies are rescaled from the raw cell sum to the calibrated
  candidate energy and summed: `signalFraction` is the attributed share of the
  candidate, `simTrackIdx` the dominant particle.

**Per jet** (`<Jet>GenMatch`): each constituent contributes its clustering
weight times its signal fraction times its momentum vector; the pT of the
vector sum over the jet divided by the gen jet pT is `signalPtRatio`. The
difference to the plain `ptRatio` of the same jet is the pile-up contribution,
jet by jet. The shared-energy response is the stricter observable: it keeps
only the shares whose particle descends from the matched gen jet's own
constituents.

Two details to keep in mind:

* "Signal" means any particle of the hard-scatter event, including the
  underlying event and other jets of that event, not only the gen jet in
  question; the shared-energy response is the one restricted to the gen jet.
* The cap by the simulated cell energy is what protects against pile-up
  sitting on top of a small signal deposit: without it, a cell with 50 MeV of
  signal and 2 GeV of pile-up would be attributed entirely to the signal
  particle.

As a result the raw PF, CHS and Puppi jets show what each mitigation leaves
in at the pile-up of the sample, while the signal part is independent of it.
On the production (2026 conditions), central jets at 15 to 30 GeV read
PF 1.46, CHS 1.19, Puppi 0.97 raw, and 0.80, 0.77, 0.77 for the signal part.

## 4. Results

Production of 16 October 2026: 30 files of the sample, 56 119 events, 299
Condor jobs (`samples_workflows/run3_rawsim/submit_rawsim_bdriver.sh`,
`MAX_FILES=30`; a second pass of the same files added the Puppi JEC factors),
analysed with `analysis/TrueJES/run_truejes.sh`. Hadronic
gen jets above 5 GeV: 301 k in total, 96.6 k in the barrel (|eta| < 1.3),
87.0 k in 1.3 < |eta| < 2.5. All jets are raw (no JEC); the sim-level deposits
are on the digitiser's GeV scale, not calibrated. The plots quoted below are in
`docs/figures/` (copies of `analysis/TrueJES/plots/`).

### 4.1 Two response observables

* `ptRatio`, <pT/pT_GEN> of the matched jet (`response_vs_pt/ladder_<region>`):
  what one usually calls the response. At low pT it includes whatever foreign
  energy the matched jet picked up (underlying event, neighbours), which the
  purity requirement allows up to 50%.
* the shared-energy response <E_shared/E_GEN> (`response_vs_pt/shared_<region>`):
  only the energy of the matched jet that descends from the gen jet. It is the
  retention of the gen jet's own energy through the step and is free of the
  foreign-energy pick-up. The two differ exactly where the gen jet is small
  compared to its surroundings.

### 4.2 The barrel ladder

Mean response in three gen-pt bins, |eta| < 1.3 (plain ratio / shared-energy
response):

| step | 13 to 16 GeV | 30 to 40 GeV | 100 to 150 GeV |
|---|---|---|---|
| SimJet (decays, conversions) | 1.00 / 0.85 | 0.96 / 0.91 | 0.97 / 0.95 |
| SimCaloJet (calorimeter deposits) | 0.72 / 0.63 | 0.77 / 0.74 | 0.91 / 0.90 |
| SimPFJet (ideal particle flow) | 0.87 / 0.79 | 0.91 / 0.88 | 0.95 / 0.95 |
| PF jet, signal part | 0.80 / 0.72 | 0.84 / 0.80 | 0.89 / 0.88 |
| CHS jet, signal part | 0.77 / 0.71 | 0.82 / 0.79 | 0.88 / 0.87 |
| Puppi jet, signal part | 0.77 / 0.73 | 0.81 / 0.79 | 0.87 / 0.86 |
| PF jet, raw (with pile-up) | 1.46 | 1.35 | 1.07 |
| CHS jet, raw | 1.19 | 1.05 | 0.97 |
| Puppi jet, raw | 0.97 | 0.93 | 0.93 |

Reading the ladder from the top:

1. **Decays in flight and conversions** cost 15 to 18% of the gen jet energy
   below 15 GeV and 4% above 100 GeV (shared-energy response 0.82 to 0.96):
   the neutrinos of pi and K decays and the decay daughters that leave the
   cone. The plain ratio hides this at low pT, where the matched sim jet also
   collects foreign energy: 1.18 at 5 to 6 GeV, 1.00 at 13 to 16 GeV, 0.96 to
   0.97 above 20 GeV.
2. **The calorimeter** is the largest single effect at low pT: the deposits
   retain 0.63 of the gen jet energy at 13 to 16 GeV (0.75 of what entered the
   calorimeter), rising to 0.94 at 150 to 300 GeV. This is the hadron
   non-linearity of a non-compensating calorimeter, isolated from everything
   else: no clustering, no thresholds, no pile-up, no tracking.
3. **Ideal tracking** recovers most of it: 0.79 at 13 to 16 GeV, 0.95 at
   150 GeV. The remaining gap to the decay-only line is the calorimeter
   response of the neutral part of the jet (photons close to 1, neutral
   hadrons well below).
4. **The reconstruction** takes a further 6 to 8% of the signal energy at all
   pT (PF signal part 0.72 versus 0.79 at 13 to 16 GeV, 0.88 versus 0.95 at
   100 to 150 GeV): thresholds, clustering and the raw PF energy scale. CHS
   and Puppi remove 1 to 3% more of the *signal*: charged signal particles
   assigned to pile-up vertices, and neutral signal down-weighted by Puppi.
5. **Pile-up** (2026 conditions) adds 0.5 to 0.6 of the gen pT to a raw PF
   jet at 15 to 30 GeV and 7% at 100 GeV; CHS leaves 0.2 at 15 GeV, Puppi
   removes it to within a few percent, at the price of the signal loss above.

The response distributions (`response_dist/HB_pt13to20`,
`response_dist/HB_pt30to50`) show the same ordering as shapes: a narrow SimJet
peak at 1, the calorimeter deposits broad and centred near 0.7, the ideal PF
and the reconstructed signal parts in between.

### 4.3 Matching efficiency and the low-pT bias

`efficiency/efficiency_HB`: the fraction of gen jets with a matched partner.
SimJet and SimPFJet match 94% of the gen jets at 13 to 16 GeV, SimCaloJet 61%,
the signal part of PF 75%, CHS 70%, Puppi 53%; the raw PF jet with the purity
requirement only 10%, because at that pT a raw PF jet is mostly pile-up (the
signal-only and shared-energy responses do not apply the purity requirement
for that reason). Below about 10 GeV the calorimeter-level and reconstructed
jets fall below the 5 GeV clustering threshold after their response, so the
matched subset is biased high (SimCaloJet 1.17 at 5 to 6 GeV with 10%
efficiency). The next production should lower `jetPtMin` to 2 or 3 GeV for
those collections to extend the ladder down.

### 4.4 Endcap, 1.3 < |eta| < 2.5

`response_vs_pt/ladder_HE1`: the decay-only ratio is lower than in the barrel
(0.85 to 0.88 at 20 to 50 GeV), the calorimeter deposits 0.75 to 0.78 and the
ideal PF 0.77 to 0.82. The reconstructed signal part is *higher* than the ideal
PF at low pT (0.93 at 10 to 20 GeV): the PF candidates carry calibrated
cluster energies while the sim-level deposits are raw, so step 6 also contains
the PF calorimeter calibration, which matters most where the raw deposits are
lowest. The sim-level steps should be read as raw-deposit steps; a calibration
of the deposits (from the single-particle `SimCalo_response`) would separate
the two.

### 4.5 JEC-corrected Puppi jets

The second production stores the GlobalTag AK4PFPuppi correction factors of
every raw Puppi jet (`PFJetPuppi_jecL1`, `PFJetPuppi_jecL1L2L3`; L1FastJet is
unity for Puppi by construction). CHS has no valid corrections in CMSSW, so
only Puppi is corrected. Two corrected observables
(`response_vs_pt/puppijec_<region>`):

* the raw Puppi jet times the full L1FastL2L3 factor: the corrected response
  as an analysis sees it;
* the signal part of the Puppi jet times the L2L3 part only: the signal has
  no pile-up left to subtract, so applying L1 to it would be wrong.

| region, gen pT | Puppi raw | Puppi corrected | signal part raw | signal part corrected (L2L3) |
|---|---|---|---|---|
| barrel, 13 to 16 GeV | 0.97 | 1.11 | 0.77 | 0.88 |
| barrel, 30 to 40 GeV | 0.93 | 1.05 | 0.81 | 0.91 |
| barrel, 100 to 150 GeV | 0.92 | 1.03 | 0.87 | 0.96 |
| endcap, 13 to 16 GeV | 1.07 | 1.26 | 0.80 | 0.95 |
| endcap, 30 to 40 GeV | 0.93 | 1.12 | 0.77 | 0.93 |

Above 50 GeV the corrections do what they should: the corrected Puppi jet is
within 1 to 3% of unity in the barrel. Below 30 GeV the corrected jet
over-shoots, 1.11 at 13 to 16 GeV in the barrel and 1.26 in the endcap, while
the corrected signal part stays below one (0.88, 0.95). The gap between the
two is the pile-up that Puppi leaves in the jet at the 2026 conditions of this
sample and that the GlobalTag corrections, derived on another campaign, do not
remove: about 0.2 of the gen pT at 15 GeV in the barrel. The signal part
corrected with L2L3 only falls short of unity by 4 to 12%, which is the part
of the signal loss (thresholds, Puppi down-weighting of signal, out-of-cone)
that the corrections absorb together with the residual pile-up in their
derivation and therefore do not restore here. The two curves bracket the
"true" jet energy scale question: corrections tuned to make the full jet
unity on their own sample necessarily over-correct the signal when the
pile-up conditions differ.

### 4.6 Caveats

* HF deposits are not calibrated (shower-library photoelectrons times the HF
  factor), so the |eta| > 3 region of the sim-level steps is not meaningful.
* The track to TrackingParticle link is by chi2 on this premixed sample; a few
  percent of the charged attributions are ambiguous.
* The 5 GeV clustering threshold biases every collection below 10 GeV (4.3).

## 5. Where things are

* Figures for presentations: `analysis/TrueJES/illustrations/`
  (`TrueJES_illustrations.pdf` collects them with a short text each).
* Result plots of the October 2026 production: `docs/figures/truejes_*` (pdf
  and png); the full set, organised in `response_vs_pt/`, `efficiency/` and
  `response_dist/`, is regenerated by `analysis/TrueJES/run_truejes.sh`.
* The Picos: `/eos/user/t/tchatzis/run3_rawsim/DYto2Mu-4Jets_Bin-MLL-50_v2/`
  (with the Puppi JEC factors; the first pass without them is in
  `DYto2Mu-4Jets_Bin-MLL-50/`).
* Pico tables and their documentation: `PicoProducer/README.md`
  ("Sim jets and the SimJet to GenJet matching", "Reconstruction-level truth",
  "PF block tables"), producers in `PicoProducer/plugins/README.md`.
* The chain that makes the Picos: `PicoProducer/python/samples_workflows/run3_rawsim/`.
* The analysis: `analysis/TrueJES/`.
