# TrueJES: the jet energy scale decomposed along the truth ladder

Histograms and plots of <pT/pT_GEN> vs pT_GEN at every step from the
generator to the reconstruction, on the Reco2Pico `run3_rawsim` Picos
(table groups `genparts`, `sim`, `simcalo`, `recojets`; see
`PicoProducer/README.md`, sections "Sim jets and the SimJet to GenJet matching"
and "Reconstruction-level truth"). Built on `../SkimRDFAnalysisBase`.
The physics write-up is `../../docs/TrueJES.md`; its section 1.1 defines every jet of the ladder in detail.

## The ladder (nine rungs, the last one being what an analysis sees)

| step | jet | what it adds |
|---|---|---|
| Sim | `SimJet` | the calorimeter-entrance particles with their production momenta: decays in flight, conversions and interactions in the tracker (the particle list) |
| SimBoundary | `SimBoundaryJet` | the same particles with their momentum at the calorimeter face: energy loss in the tracker material and bending |
| SimCalo | `SimCaloJet` | the calorimeter response (sim-hit deposits per entrance particle) |
| SimCaloCell | `SimCaloCellJet` | the same deposits clustered as cells: the shower geometry instead of one direction per particle |
| SimPF | `SimPFJet` | ideal particle flow: perfect tracking for charged particles in acceptance, deposits otherwise |
| PF, CHS, Puppi | `PFJet`, `PFJetCHS`, `PFJetPuppi` | the reconstruction, raw (no JEC), with the pile-up of the sample and its mitigation |
| PFSig, CHSSig, PuppiSig | same | `signalPtRatio`: the response of the signal-attributed part of the reconstructed jet (pile-up removed by attribution) |
| PuppiCorr, PuppiSigCorr | `PFJetPuppi` | the Puppi levels times the GlobalTag JEC factors stored in the Pico: the full L1FastL2L3 factor on the raw jet, the L2L3 part only on the signal part (no pile-up left to subtract). Present when the Pico has `PFJetPuppi_jecL1L2L3`. CHS has no valid corrections in CMSSW, so only Puppi is corrected. |

Every step is matched to the same `GenJet` through the ancestry scores of the
Pico (`*GenMatch` tables): a gen jet counts as matched at a step when the pair
flagged best for it has `genFraction >= min_gen_fraction` and
`simFraction`/`recoFraction >= min_other_fraction` (both 0.5 by default,
`truejes_config.yaml`). No deltaR is used. Gen jets within 0.4 of a generator
muon above 10 GeV (the Z decay) are excluded.

## Files

| file | purpose |
|---|---|
| `truejes_rdf_definition.py` | RDF definition: per-gen-jet response columns per step, eta regions (Incl, HB, HE1, HE2, HF) and gen-pt bins as masks |
| `make_histograms_yaml.py` | writes `truejes_histograms.yaml`: per step and region a TProfile of the response vs pT_GEN, a TProfile of the match efficiency, a TH2 and the response distributions per gen-pt bin |
| `truejes_config.yaml` | matching thresholds and the lepton veto |
| `run_truejes.sh [INPUT_DIR] [TAG]` | histograms (`output<TAG>/truejes.root`) and plots (`plots<TAG>/`) |
| `illustrations/` | TikZ figures of the ladder, the matching, the calorimeter-entrance rule, the deposits, the attribution and the PF block tables, with a summary PDF (`make`) |
| `plot_truejes.py` | the plots, each as `.pdf` and `.png`, in `response_vs_pt/` (`ladder_sim_<region>` the simulation-level steps, `ladder_reco_<region>` the reconstructed ones with the ideal PF as the reference, `reco_<region>` raw vs signal-only, `shared_sim_<region>` / `shared_reco_<region>` shared-energy response, `puppijec_<region>` raw and JEC-corrected Puppi; with the pile-up truth of `run3_mix`: `ladder_pileup_<region>` the ideal jets with pile-up against the raw reconstructed ones, `pileup_pf_<region>` SimPFPUJet vs the raw PF jet and `pileup_chs_<region>` SimPFPUCHSJet vs the raw CHS jet, each with the signal part and the ideal PF without pile-up), `efficiency/` (`efficiency_sim_<region>`, `efficiency_reco_<region>`), `response_dist/` (`<region>_<ptbin>_sim`, `_reco`), `composition/` (`composition_<region>_<coll>`: the fraction of the gen jet pT carried by each flavour component at the generator, in the ideal PF and in the signal part of the reconstructed jet, i.e. how much of each component survives); every level keeps its colour and marker across figures and `offset/` (`offset_vs_pt_<region>` with the three collections, `offset_vs_pt_<region>_<coll>` stacked by candidate type, and the same vs |eta| per gen-pt bin as `offset_vs_eta_<ptbin>[_<coll>]`) |

## Running

```bash
cmsenv
./run_truejes.sh /eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_rawsim/DYto2Mu-4Jets_Bin-MLL-50_v4
# plots also mirrored to /eos/user/t/tchatzis/php-plots/TrueJES (WEB_DIR=... to change, WEB_DIR= to skip)
```

Env: `THREADS` (8), `MAX_EVENTS` (-1), `FILE_PATTERN` (`*.root`). The plotting
needs mplhep and matplotlib (see the base README).

## Observables

* `Resp_<step>_<region>`: TProfile of `ptRatio` (pT/pT_GEN of the matched jet) vs pT_GEN.
* `RespShared_<step>_<region>`: TProfile of `sharedEnergy / E_GEN`, the energy of the matched
  jet that descends from the gen jet; immune to the foreign energy a matched jet picks up.
* `Eff_<step>_<region>`: matched fraction vs pT_GEN.
* `RespDist_<step>_<region>_<ptbin>`: response distributions per gen-pt bin.
* `Offset_<coll>_<type>_<region>` and `OffsetEta_<coll>_<type>_<ptbin>`: TProfile of the
  offset of the matched reconstructed jet (PF, CHS, Puppi), i.e. the scalar sum over its
  constituents of clustering weight times (1 - signalFraction) times pT, the pile-up and
  noise it contains, split by PF candidate type (charged hadrons, photons, neutral
  hadrons, HF hadrons, HF EM, leptons/other, total), vs pT_GEN per eta region and vs
  |eta_GEN| per gen-pt bin. The matching requires genFraction only.

The purity requirement applies to `ptRatio` only; the signal-only (`*Sig`) and
shared-energy responses count the gen jet's own energy by construction.

Every jet collection (GenJet, the simulation-level jets, raw PF/CHS/Puppi) is
clustered with `jetPtMin = 5 GeV`, and a jet below it is simply absent, so the gen
jet counts as unmatched. The cut acts on the jet's total pT, signal plus pile-up
and noise. In the lowest gen-pt bins the efficiency and the response are
therefore threshold-dominated: the simulation-level jets must pass 5 GeV on the
signal alone (SimPF median response 0.96 in 5-8 GeV, an upward-truncated
distribution), while raw PF and CHS jets are lifted over it by the pile-up offset
(PFSig median 0.63, CHSSig 0.54: the signal part alone would mostly fail). This is
why the PF and CHS signal-part efficiencies exceed the ideal PF below about
7 GeV, and why Puppi, which removes the pile-up, falls below it. Read the
efficiencies and the response below ~20 GeV with this in mind; lowering
`jetPtMin` of the non-gen collections removes the effect.

Results and their reading: `../../docs/TrueJES.md`, section 4.

## Pile-up

No pile-up matching between samples is needed: the Pico attributes every PF
candidate to the simulated particles of the signal event, so `signalPtRatio`
is the response of the jet without its pile-up, jet by jet, while `ptRatio`
of the raw PF, CHS and Puppi jets shows what each mitigation leaves in. The
sample is Run3Winter26 with 2026 pile-up conditions.

## The Picos these scripts need

| script | Pico | how it is produced |
|---|---|---|
| `run_truejes.sh` (`make_histograms_yaml.py`, `truejes_rdf_definition.py`, `plot_truejes.py`): the ladder, the efficiencies, the offsets by candidate type, the compositions | `run3_rawsim` Picos (premixed sample): groups `genparts`, `sim`, `simcalo`, `recojets` with `pfcands`, `jets`, `muons`; current set `/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_rawsim/DYto2Mu-4Jets_Bin-MLL-50_v4` | `PicoProducer/python/samples_workflows/run3_rawsim/submit_rawsim_bdriver.sh --submit` (RAW+GEN-SIM -> RECO -> Pico; the Pico step runs `RECO_to_pico_cfg.py` with `tables=event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim,simcalo,recojets`) |
| the same, pile-up figures (`ladder_pileup`, `pileup_pf`, `pileup_chs`, `offset/pileup_vs_*`, the SimCaloCellPU/SimPFPU/SimPFPUCHS levels) | `run3_mix` Picos (classically mixed, pile-up truth): the groups above plus `pileupTruth=picoMixedTruth`; `/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix/DYto2Mu-4Jets_Winter26` | `PicoProducer/python/samples_workflows/run3_mix/submit_mix_bdriver.sh --submit` (GEN-SIM + minimum-bias GEN-SIM -> DIGI with the mixing module -> RECO -> Pico with `pileupTruth=picoMixedTruth`) |
| `illustrations/` | none | `illustrations/build_figures.sh` (make, PNGs, copies into `docs/figures`) |

The scripts take any directory of Picos (`run_truejes.sh <dir> <tag>`); the
per-cell pulse and rechit studies live in `../CaloPulses`.
