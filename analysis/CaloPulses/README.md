# CaloPulses: one calorimeter cell from the deposits to the rechit

What the pulse fits of the reconstruction (multifit in ECAL, MAHI in HCAL) make
of the overlapping bunch crossings, cell by cell, on the classically mixed Picos
of `PicoProducer/python/samples_workflows/run3_mix` (pile-up truth per
crossing) with the `rechits` group and, when the digis were kept, the
`calodigis` group. The physics write-up is `../../docs/CaloPulses.md` (the chain from the deposit to the rechit, the parametrisations, what the Picos carry); the leak numbers are in section 5.1 of `../../docs/TrueJES.md`.

## Files

| file | purpose |
|---|---|
| `plot_cell_pulse.py` | one cell per figure, `plots/cells_matching_cases/<case>_<sub>_<event>` with the cases `signal_only`, `signal_pileup`, `pileup_only`, `out_of_time`: left the simulated deposits per bunch crossing (signal and in-time pile-up at 0, the out-of-time interactions at -5..+3 and the sum of the earlier ones) next to the rechit split by the attribution into signal, pile-up and residual; right the pulse shapes of the deposits (the detector templates of `pulse_shapes.json`, peak set to the deposit) summed, with the digi samples of the cell when the Pico has them (`EBDigi`/`HBHEDigi`) and otherwise the sample times only |
| `measure_pulse_leak.py` | the weight with which each bunch crossing's deposit enters the in-time rechit, per subdetector: from the cells one crossing dominates, and from a non-negative regression on all crossings; the in-time weight is the rechit scale of the sim deposits, the others the leak of the fit; also the in-time weight per deposit bin, where the readout thresholds show |
| `dump_pulse_shapes.py` | writes `pulse_shapes.json` (needs cmsenv): the HCAL reconstruction pulse template (`HcalPulseShapes` id 208, the Run-3 MC SiPM shape of the global tag's `HcalRecoParams`) and the ECAL simulation pulse (`EcalSimPulseShape` payload of the global tag), sampled every nanosecond |
| `pulse_shapes.json` | the templates above, as produced for `150X_mcRun3_2026_realistic_v4` |

## The Picos these scripts need

Both scripts read a Pico of the classically mixed chain with the pile-up truth
(`pileupTruth=picoMixedTruth`: the per-crossing cell columns
`SimCaloCell_ootBxm5` ... `ootBxp3`, `ootEarly`) and the `rechits` group with
**every** ECAL rechit (`fullEcalRecHits=True`; the default tables take the
reduced ECAL collections, which cover 2% of the cells). The digi tables need
the RAW file of the chain (`step0.root`) as the secondary input of the Pico
step, since the RECO files do not carry the digis:

```bash
# after run_mix_local.sh or run_chain.sh (step0.root = RAW + truth, step1.root = RECO)
cmsRun $CMSSW_BASE/src/Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=file:step1.root secondaryInputFiles=file:step0.root \
  output=pico.root isMC=true era=Run3_2025 globalTag=150X_mcRun3_2026_realistic_v4 \
  tables=event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim,simcalo,recojets,rechits,calodigis \
  pileupTruth=picoMixedTruth fullEcalRecHits=True digiMinAmplitude=0.1
```

`PicoProducer/python/samples_workflows/run3_mix/produce_digi_sample.sh [NEVENTS] [SKIP]`
runs exactly this chain (about 2.5 hours per 200 events) and copies the Pico
to the directory below. Samples made this way (200 events each, locally):

| Pico | content |
|---|---|
| `/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix/local_200ev/pico_200ev_fullEcalRecHits.root` | events 0-199 of the first DY GEN-SIM file, every ECAL rechit, no digis; `pulse_leak_200.txt` next to it is the output of `measure_pulse_leak.py` |
| `/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix_digis/DYto2Mu-4Jets_Winter26/` | the same with the `EBDigi`, `EEDigi`, `HBHEDigi` tables (digis above 0.1 GeV) |

## Running

```bash
cmsenv
python3 dump_pulse_shapes.py                       # once per global tag
python3 plot_cell_pulse.py --input <pico> --output-dir plots --events 3
python3 measure_pulse_leak.py <pico> [<pico> ...]
```

The figures are mirrored to `/eos/user/t/tchatzis/php-plots/CaloPulses/`.

## What the digis showed (10 events, `step2_pico_digis.root`)

* ECAL: the pedestal-subtracted samples on the rechit scale (with the laser
  correction, 1.4 to 1.6 in this Run-3 MC, without which the samples miss the
  rechit by that factor) sit on the simulation pulse scaled to the deposit;
  a crossing `b` peaks at sample `5 + b`, as the templates assume.
* HCAL: the in-time pulse starts in the sample of interest, but the small
  out-of-time pulses appear 10 to 15 ns later than `25 ns x b` relative to
  it: the QIE time slew delays small charges (it is in the digitiser and in
  MAHI's model) is the parametrised effect of that size, though it has not
  been isolated as the cause. The crossing before the in-time one puts half
  its rise into the in-time sample, which is why it leaks a third of its
  deposit into the HB rechit (`measure_pulse_leak.py`). The figures keep the
  templates at `25 ns x b`; the digi samples show the real timing.
