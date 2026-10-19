# TrueJES: the jet energy scale decomposed along the truth ladder

Histograms and plots of <pT/pT_GEN> vs pT_GEN at every step from the
generator to the reconstruction, on the Reco2Pico `run3_rawsim` Picos
(table groups `genparts`, `sim`, `simcalo`, `recojets`; see
`PicoProducer/README.md`, sections "Sim jets and the SimJet to GenJet matching"
and "Reconstruction-level truth"). Built on `../SkimRDFAnalysisBase`.
The physics write-up is `../../docs/TrueJES.md`.

## The ladder

| step | jet | what it adds |
|---|---|---|
| Sim | `SimJet` | decays in flight and conversions (Geant4 particle list) |
| SimCalo | `SimCaloJet` | the calorimeter response (per-particle sim-hit deposits) |
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
| `illustrations/` | TikZ figures of the ladder, the matching, the terminal rule, the deposits, the attribution and the PF block tables, with a summary PDF (`make`) |
| `plot_truejes.py` | the plots, each as `.pdf` and `.png`, in `response_vs_pt/` (`ladder_<region>`, `reco_<region>` raw vs signal-only, `shared_<region>` shared-energy response, `puppijec_<region>` raw and JEC-corrected Puppi), `efficiency/` (`efficiency_<region>`) and `response_dist/` (`<region>_<ptbin>`) |

## Running

```bash
cmsenv
./run_truejes.sh /eos/user/t/tchatzis/run3_rawsim/DYto2Mu-4Jets_Bin-MLL-50
```

Env: `THREADS` (8), `MAX_EVENTS` (-1), `FILE_PATTERN` (`*.root`). The plotting
needs mplhep and matplotlib (see the base README).

## Observables

* `Resp_<step>_<region>`: TProfile of `ptRatio` (pT/pT_GEN of the matched jet) vs pT_GEN.
* `RespShared_<step>_<region>`: TProfile of `sharedEnergy / E_GEN`, the energy of the matched
  jet that descends from the gen jet; immune to the foreign energy a matched jet picks up.
* `Eff_<step>_<region>`: matched fraction vs pT_GEN.
* `RespDist_<step>_<region>_<ptbin>`: response distributions per gen-pt bin.

The purity requirement applies to `ptRatio` only; the signal-only (`*Sig`) and
shared-energy responses count the gen jet's own energy by construction.
Results and their reading: `../../docs/TrueJES.md`, section 4.

## Pile-up

No pile-up matching between samples is needed: the Pico attributes every PF
candidate to the simulated particles of the signal event, so `signalPtRatio`
is the response of the jet without its pile-up, jet by jet, while `ptRatio`
of the raw PF, CHS and Puppi jets shows what each mitigation leaves in. The
sample is Run3Winter26 with 2026 pile-up conditions.
