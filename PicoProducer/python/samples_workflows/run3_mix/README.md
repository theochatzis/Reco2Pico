# run3_mix: classically mixed Run-3 chain with the pile-up truth

The premixed Run-3 samples (`../run3_rawsim`) carry the signal truth only: the
pile-up is a pre-digitised library whose particles and sim hits are gone. This
chain mixes the signal GEN-SIM with minimum-bias GEN-SIM events in the DIGI
step the classical way (`MixingModule` reading the minimum-bias files), and
keeps what the mixing module builds for the digitisers: the pile-up
interactions' SimTracks, SimVertices and calorimeter sim hits, each tagged with
its interaction and bunch crossing. Every calorimeter cell is then signal
deposit plus a known list of pile-up deposits plus noise, and the pile-up of a
reconstructed jet can be decomposed into its true origins (see
`docs/TrueJES.md`, section 5).

```
GEN-SIM (DY)  +  minimum-bias GEN-SIM  --step0 DIGI,L1,DIGI2RAW (mix)-->  RAW + sim truth + pile-up truth
   --step1 RAW2DIGI,L1Reco,RECO,RECOSIM-->  RECOSIM + truth  --RECO_to_pico pileupTruth=picoMixedTruth-->  Pico
```

| file | role |
|---|---|
| `mixCustomise.py` | `pileupTruth`: adds `PicoMixedTruthProducer` (label `picoMixedTruth`) after the mixing module and keeps its products with the signal truth; `keepPileupTruth`: passes them through the RECO output |
| `make_mix_cfgs.sh [OUTDIR]` | builds `step0_DIGI_cfg.py` (`--pileup PU_SCENARIO --pileup_input` the files of `PU_INPUT`), `step1_RECO_cfg.py` and the ntuple cfg, with the VarParsing tail |
| `minbias_files.txt` | the minimum-bias GEN-SIM files read by the mixing (one per line; the central Winter26PU sample copied to the group EOS area) |
| `steps_mix_chain.json` | sample steps after step0: the RECO step |
| `run_mix_local.sh [NEVENTS] [INPUT]` | local end-to-end test |
| `produce_digi_sample.sh [NEVENTS] [SKIP] [WORKDIR]` | a small Pico sample with the digis, locally: step0, step1, then the Pico with every ECAL rechit and the `calodigis` group (the RAW step0 as secondary input), copied to `.../reco2pico/run3_mix_digis/DYto2Mu-4Jets_Winter26/` (see `analysis/CaloPulses/README.md`) |
| `submit_mix_bdriver.sh [--submit] [--dry-run]` | Condor production through `../common/submit_bdriver_chain.sh` |
| `datasets/DYto2Mu-4Jets_Winter26_GEN-SIM.json` | the DY GEN-SIM files copied to the group EOS area (the central sample is mostly on tape) with their event counts |

## Inputs

* Signal: `/DYto2Mu-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Winter26wmLHEGS-150X_mcRun3_2026_realistic_v2-v2/GEN-SIM`,
  the parent of the premixed sample of `../run3_rawsim` (23 M events, 525 kB
  per event, on disk at PIC and JINR for a few blocks only). Files of a
  disk-resident block are copied to
  `/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/gensim/DYto2Mu-4Jets_Winter26/`
  and listed in the dataset JSON.
* Pile-up: `/MinBias_TuneCP5_13p6TeV-pythia8/Run3Winter26GS-Winter26PU_150X_mcRun3_2026_realistic_v1-v1/GEN-SIM`,
  the library the Winter26 premix was built from (98 M events, 196 kB per
  event, 103 k events per 20 GB file). Files are copied to
  `.../reco2pico/gensim/MinBias_Winter26PU/` and listed in `minbias_files.txt`.
* Pile-up profile: `2025_LHC_Simulation_fill12p5h_levelling9h_nb2340_xSec80mb_il2p23`
  (mean 64.3 interactions, 5 to 95% range 44 to 82), which matches the
  premixed sample (`Pileup_nTrueInt` mean 64.8). Out-of-time crossings -12 to
  +3 (25 ns), as in the central mixing.

## What the pile-up truth contains (`picoMixedTruth`)

| product | content |
|---|---|
| `SimTracks`/`SimVertexs` `pileup` | the SimTracks and SimVertices of the in-time pile-up interactions (bunch crossing 0), with their `EncodedEventId`; vertex indices renumbered into the merged collection |
| `PCaloHits` `EcalHitsEB`, `EcalHitsEE`, `EcalHitsES`, `HcalHits` | the calorimeter sim hits of the in-time pile-up interactions, hit by hit, with event id and Geant4 track id |
| `PCaloHits` `OotEcalHitsEB`, ... `OotHcalHits` | the out-of-time pile-up deposits summed per (cell, bunch crossing), event id = (bx, 0) |
| `int` `nInTime` | number of in-time interactions |

With `pileupTruth=picoMixedTruth` the Pico gains: `SimCaloCell_puEnergy`,
`SimCaloCell_ootEnergy`, `SimCaloCell_nPU`; `PFCandTruth_puFraction` (the
share of every PF candidate attributed to in-time pile-up: the track of a
pile-up TrackingParticle, or the pile-up share of the cluster cells, with the
cap now the full in-time sim energy of the cell); and three jets with pile-up
and their gen-jet matches: `SimCaloCellPUJet` (cells with signal + in-time
pile-up deposits), `SimPFPUJet` (ideal PF of signal + pile-up particles) and
`SimPFPUCHSJet` (the same without the trackable charged pile-up: a perfect
charged-hadron subtraction). The pile-up entrance particles are built by a
second `PicoCaloEntranceProducer` (`picoCaloEntrancePU`) on the pile-up
SimTracks with the pile-up hits.

## Cost

Classical mixing at 65 interactions with 16 bunch crossings reads about a
thousand minimum-bias events per signal event, which is why premixing exists:
the DIGI step takes minutes per event and several GB of memory, hence
`EVENTS_PER_JOB=50`, `MEMORY=8G`, `RUNTIME=20:00:00` and the `tomorrow` job
flavour by default. The minimum-bias files must be read locally (EOS), not
through the global redirector.
