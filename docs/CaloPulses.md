# CaloPulses: from the simulated deposit to the rechit, one cell at a time

The attribution of the reconstructed jets (TrueJES.md, section 3) works on
rechits: one energy per calorimeter cell, set against the Geant4 deposits of
that cell per particle and per bunch crossing. A rechit is not a deposit. It
is the amplitude a pulse fit assigns to the in-time bunch crossing from the
digitised samples of the cell, in which the pulses of up to ten crossings
overlap. This note explains that chain for ECAL and HCAL as the Run-3
simulation and reconstruction implement it, which of its pieces the Picos
carry on the reconstruction side (the digis) and on the simulation side (the
deposits per crossing and the pulse templates), and what the figures of
`analysis/CaloPulses` show. The parametrisations are quoted from the CMSSW
release used here (`CMSSW_15_0_4`, global tag
`150X_mcRun3_2026_realistic_v4`); file paths are relative to its `src`.

Samples: the classically mixed 200-event Picos with the digis in
`/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix_digis/DYto2Mu-4Jets_Winter26/`
(`pico_digis_events0to199.root`, `pico_digis_events200to399.root`), made with
`PicoProducer/python/samples_workflows/run3_mix/produce_digi_sample.sh`.

## 1. The chain

```
Geant4 hits (energy, time, per particle and crossing)
   -> analogue pulse of the cell: sum of one pulse shape per hit, at the hit time
   -> front end: samples every 25 ns (ECAL 10 samples, HCAL 8 or 10 buckets of integrated charge)
   -> digi: ADC codes (+ gain id in ECAL, + TDC and capacitor id in HCAL)
   -> pulse fit (ECAL multifit, HCAL MAHI): one amplitude per bunch crossing
   -> rechit: the in-time amplitude on the energy scale
```

The simulation stops being exact at the second line: from there on the
digitiser adds noise, the front-end non-linearities and the readout
threshold, and the fit has to undo the overlap of the crossings. Everything
the attribution calls "residual" (noise, out-of-time pile-up, calibration) is
made in these steps.

## 2. ECAL

**Pulse shape.** Every hit deposits its energy as a pulse of fixed shape at
the hit time. The simulation takes the shape from the conditions database
(record `EcalSimPulseShapeRcd`, tag `EcalSimPulseShapePhaseI` in this global
tag): three tables of 500 values at 1 ns steps, for the barrel, the endcaps
and the APD, read by `SimCalorimetry/EcalSimAlgos` (`EBShape`, `EEShape`,
`EcalShapeBase`;
https://github.com/cms-sw/cmssw/tree/CMSSW_15_0_4/SimCalorimetry/EcalSimAlgos).
The tables are measured in the detector and live only in the database
(`conddb --db pro dump` of the payload prints them); no paper gives them. The barrel shape rises from 10% to 90% in 26 ns, peaks
44 ns after the 10% point, and is still at 0.88 of the peak 25 ns later,
0.67 after 50 ns, 0.47 after 75 ns and 0.32 after 100 ns; it is at 0.77 of
the peak 25 ns before it and at zero 50 ns before. The endcap shape is a
little slower (35 ns rise). This is the shape drawn in the figures
(`pulse_shapes.json`, from `dump_pulse_shapes.py`).

**Front end and digi.** The multi-gain pre-amplifier (MGPA) shapes the
photodetector signal and three gain stages (x12, x6, x1) are sampled at
40 MHz by a 12-bit ADC; the digi keeps ten samples with the gain id of each
(1: x12, 2: x6, 3: x1, 0: saturated), the in-time pulse peaking at the sixth
(`SimCalorimetry/EcalSimAlgos/src/EcalElectronicsSim.cc`,
`EcalCoder.cc`). The pedestal of each gain and the gain ratios are
conditions (`EcalPedestals`, `EcalGainRatios`).

**Multifit** (`RecoLocalCalo/EcalRecAlgos/src/EcalUncalibRecHitMultiFitAlgo.cc`,
`PulseChiSqSNNLS.cc`; `ecalMultiFitUncalibRecHit`). The ten pedestal-subtracted
samples `S_i` are fitted with a sum of pulses, one per bunch crossing from
-5 to +4 (`activeBXs`), all of the same template shifted by 25 ns each:

```
chi2 = (S - P A)^T  C^-1  (S - P A),     A_b >= 0
```

where `P` has one column per crossing (the template at that shift), `A` the
amplitudes, and `C` the sum of the electronics noise covariance of the
crystal (per gain) and the pulse-shape covariance scaled by the amplitudes.
The non-negative least squares (NNLS) solution is found iteratively, the
covariance being updated with the amplitudes. The template is per crystal:
twelve values at the sample positions, normalised to the peak (record
`EcalPulseShapesRcd`, tag `EcalPulseShapes_mc`; covariances
`EcalPulseCovariances`). The amplitude of the in-time pulse is therefore the
height of its peak, in ADC counts at gain 12. The out-of-time amplitudes are
not stored. The method is described in JINST 15 (2020) P10002
(arXiv:2006.14359).

**Energy.** The rechit energy is

```
E = A x ADCToGeV(EB or EE) x intercalibration(crystal) x laser(crystal, time)
```

with `EcalADCToGeVConstant`, `EcalIntercalibConstants` and the laser
(transparency) correction from `EcalLaserAPDPNRatios` through
`EcalLaserDbService` (`RecoLocalCalo/EcalRecProducers`,
`EcalRecHitWorkerSimple`). In this Run-3 MC the laser correction is not 1:
it is 1.4 to 1.6 in the barrel cells looked at, the transparency loss of the
year being simulated; without it the digi samples miss the rechit by that
factor.

**Readout threshold.** Only crystals above the selective-readout thresholds
produce a rechit; on the mixed sample a rechit exists for 29% of the barrel
crystals with 0.3 to 0.6 GeV of in-time deposit and 84% with 0.6 to 1 GeV,
in the endcaps the threshold sits around 1 GeV (TrueJES.md, 5.1). This is a
signal loss the attribution counts in the residual.

## 3. HCAL (HB and HE, SiPM readout)

**Pulse shape.** The light of a scintillator tile reaches the SiPM through a
wavelength-shifting (Y11) fibre, and the shape of the signal is the
scintillator-plus-fibre time distribution convolved with the SiPM pulse.
Both are measured parametrisations hard-coded in CMSSW,
`CalibCalorimetry/HcalAlgos/src/HcalPulseShapes.cc`
(https://github.com/cms-sw/cmssw/blob/CMSSW_15_0_4/CalibCalorimetry/HcalAlgos/src/HcalPulseShapes.cc);
the comments of that file are the only record of their origin, there is no
publication of the formulas:

* the scintillator + Y11 time distribution of the 2017 measurement with a
  Landau correction term (`Y11206`), of the form
  `A (1 - exp(-(t - s)/n)) exp(-(t - s)/t0)` with `A = 0.104`, `n = 0.44 ns`,
  `t0 = 10.0 ns` and a phase shift `s = 7.2 ns`;
* the SiPM pulse from the 2016 laser measurement (`analyticPulseShapeSiPMHE`):
  the sum of two log-normal pulses, `A1 = 5.20/6.94`, `sigma = 0.539`,
  `theta = -0.40 ns`, `m = 4.43 ns` and `A2 = 1.86/6.94`, `sigma = 0.813`,
  `theta = 7.03 ns`, `m = 12.3 ns`.

Their convolution, normalised to unit integral over 250 ns, is shape 206
(`computeSiPMShapeHE206` in the same file).
The simulation uses it for every HB and HE channel (record
`HcalMCParamsRcd`, tag `HcalMCParams_2019_v1.0_mc`, `signalShape = 206`).
The reconstruction uses shape 208, the tabulated form of the same shape
(`computeSiPMShapeMCRecoRun3`, "modified shape 206, 7.2 ns shift"), set per
channel by the `HcalRecoParams` of the global tag
(`HcalRecoParams_2021_v1.1_mc`, `pulseShapeID = 208`). Shape 208 starts
7 ns after its time origin, peaks 8 ns after its start, and puts 67% of its
charge in the first 25 ns, 21% in the next, 6% in the third, 2% in the
fourth and 4% beyond 100 ns. It is the HCAL template of the figures.

**Digitiser** (`SimCalorimetry/HcalSimAlgos/src/HcalSiPMHitResponse.cc`,
`HcalSiPMShape`). Every Geant4 hit is converted to a number of
photoelectrons (the sampling factors of `hcalSimParameters_cfi.py`, which put
the deposits on the GeV-equivalent scale the Pico uses), each photoelectron
is given a time drawn from the scintillator + Y11 distribution and added to
a histogram of the cell with 0.5 ns bins (`deltaTSiPM_`), with the SiPM
response (non-linearity, cross-talk) applied; the SiPM pulse is then
convolved in and the result integrated in 25 ns buckets. The time origin is
set so that an in-time hit falls into the sample of interest
(`binOfMaximum`, `timePhase` 5 ns for HB and 6 ns for HE). Pile-up hits of
crossing `b` enter with their time shifted by `25 ns x b`.

**Front end: QIE11** (`SimCalorimetry/HcalSimAlgos/src/HcalAmplifier.cc`,
`HcalCoderDb`, `HcalQIECoder`). The Charge Integrator and Encoder integrates
the SiPM current in 25 ns buckets on four rotating capacitors (`capid` 0 to
3, each with its own pedestal) and encodes the charge non-linearly on an
8-bit scale in four ranges; the charge of a code is the QIE coder of the
conditions (`HcalQIEData`, `fc0..9` of the digi table). A 6-bit TDC gives
the time at which the pulse crossed a threshold within the bucket, in
0.5 ns steps (`tdc0..9`). The digi carries 8 buckets in data and 10 in this
MC, the sample of interest flagged (`soi`).

**Time slew.** The QIE's discriminator responds later to small signals.
The simulation delays every pulse above 5 fC by

```
delay(fC) = tzero + slope x ln(fC),   capped at tmax
```

(`CalibCalorimetry/HcalAlgos/src/HcalTimeSlew.cc`, "M2" parameters of
`CalibCalorimetry/HcalPlugins/python/HcalTimeSlew_cff.py`; the Medium bias
set is `tzero = 11.98 ns`, `slope = -1.56 ns`, `tmax = 10 ns`, so 10 fC are
delayed by 8.4 ns, 100 fC by 4.8 ns and 1000 fC by 1.2 ns), applied in
`SimCalorimetry/HcalSimAlgos/src/HcalTimeSlewSim.cc`. MAHI applies the same
function to each pulse it fits, with the charge of that pulse.

**MAHI** (Minimisation At Hcal, Iteratively;
`RecoLocalCalo/HcalRecAlgos/src/MahiFit.cc`, parameters in
`RecoLocalCalo/HcalRecProducers/python/HBHEMahiParameters_cfi.py`). Yes, it
is the same idea as the ECAL multifit, a chi-square fit of the samples with
one pulse per crossing to take the out-of-time ones out:

```
chi2 = (S - P A)^T  C^-1  (S - P A),     A_b >= 0,   b = -3 ... +4
```

`S` are the pedestal-subtracted charges of the buckets (in fC), `P` has one
column per crossing: shape 208 integrated over each 25 ns bucket, shifted
by `25 ns x b` and by the time slew of that pulse's charge (the fit
iterates: the slew depends on the amplitude), `C` the covariance from the
pedestal width, the photostatistics of each pulse and the uncertainty of
the template's timing. The amplitudes are found by NNLS, iterated with the
covariance. The in-time amplitude becomes the energy, the fit also gives a
time (`calculateArrivalTime`, the "cc" time algorithm) and the chi-square,
both in the rechit; the out-of-time amplitudes are not stored. In Run 3 HB
and HE use the full eight-pulse fit for every channel (`chiSqSwitch = -1`),
with the pedestal from the conditions (`dynamicPed = False`). MAHI is
described in the Run-3 detector paper, JINST 19 (2024) P05064
(arXiv:2309.05466), section on the HCAL, and in the CMS detector
performance note DP-2018/018; the readout is that of the Phase-1 HCAL
upgrade (CERN-LHCC-2012-015).

**Energy.** For bucket `i` and the in-time amplitude alike,

```
E = (fC - pedestal(capid)) x gain(channel, capid)
```

with the pedestal and the response-corrected gain (`respcorrgain`: the
gain in GeV/fC times the response correction) of `HcalCalibrations` from
`HcalDbService`. The sim deposits of the Pico are on the digitiser's
GeV-equivalent scale, and the rechit over that scale, measured cell by cell,
is 0.74 in HB and 0.75 in HE (`RECHIT_SCALE` of `sim_cff.py`): the
difference is the pulse integral the fit does not assign to the in-time
crossing, the time slew included.

## 4. What the Picos carry

**Reconstruction side.**

| table | content | group |
|---|---|---|
| `EBRecHit`, `EERecHit`, `HBHERecHit` | the rechits: `rawId`, `energy`, `time`, `chi2`, flags | `rechits`; `fullEcalRecHits=True` for every ECAL rechit rather than the reduced collections around selected objects |
| `EBDigi`, `EEDigi` | `adc0..9`, `gain0..9`, `e0..9` = (adc - pedestal of the gain) x gain ratio to 12 x ADCToGeV x intercalibration x laser, i.e. each sample on the rechit scale; `pedestal`, `gevPerAdc`, `laser`, `saturated` | `calodigis`, unpacked from the RAW file given as secondary input |
| `HBHEDigi` | `adc0..9`, `tdc0..9`, `capid0..9`, `fc0..9`, `e0..9` = (fc - pedestal of the capacitor) x gain; `soi`, `nSamples`, `pedestal`, `gain` | `calodigis` |

The digi is the record of the cell: what the fit saw, noise and time slew
included. Nothing finer exists in data.

**Simulation side.**

| what | where |
|---|---|
| deposits per particle and per crossing in every cell: signal (`SimCaloCell_energy`), in-time pile-up (`puEnergy`, `nPU`), out-of-time per crossing -5 to +3 (`ootBxm5 ... ootBxp3`) and earlier (`ootEarly`), all on the GeV-equivalent scale | `simcalo` group with `pileupTruth=picoMixedTruth` (classically mixed chain, `PicoMixedTruthProducer`) |
| the pulse templates: shape 208 (reconstruction, HB and HE) and the ECAL simulation pulse (EB, EE), at 1 ns | `analysis/CaloPulses/pulse_shapes.json`, dumped from the release and the global tag by `dump_pulse_shapes.py` |
| the simulated analogue pulse of each HCAL cell (the photoelectron histogram at 0.5 ns, before the front end) | not in the Pico; the digitiser keeps it with `debugCaloSamples = True` (`hcalUnsuppressedDigis_cfi.py`, product `CaloSamplesCollection` "HcalSamples"), which needs a rerun of the DIGI step and a table; ECAL has no such hook, but its pulse is the template at the hit times exactly |

What the drawing cannot reproduce from the simulation side alone: the hit
times within a crossing (a few ns), the time slew, the noise and the fit.
The digi samples carry all of it.

## 5. The figures (`analysis/CaloPulses/plot_cell_pulse.py`)

One cell per figure, chosen per event and subdetector among the cells with
a rechit: `signal_only` (the largest signal deposit with no in-time
pile-up), `signal_pileup` (the most energetic cell where both exceed
0.1 GeV), `pileup_only` (the largest in-time pile-up deposit without
signal), `out_of_time` (the largest out-of-time deposit relative to the
in-time one). Left: the deposits per crossing (signal and in-time pile-up at
0, out-of-time at -5 to +3, the earlier ones summed) and, next to them, the
rechit split by the attribution into signal, pile-up and residual. Right:
the templates, one per crossing scaled to its deposit (ECAL: peak = deposit,
as the multifit amplitude is the peak; HCAL: integral = deposit, drawn per
25 ns, as MAHI's amplitude is the charge), their sum, and the digi samples
of the cell on the same scale, with the templates' prediction at the
sample times as open circles.

What they show on the 200-event sample (TrueJES.md 5.1 has the numbers):

* ECAL: the samples sit on the template; the fit takes the other crossings
  out almost entirely (3 to 4% of the neighbouring crossings' deposits leak
  into the rechit, a tenth of a percent beyond), and the in-time scale is
  1.00 where a rechit exists.
* HCAL: the in-time weight over all cells reproduces the rechit scale, and
  the crossing before the in-time one leaks a third of its deposit into HB
  (0.31) and a sixth into HE (0.16), the others 2 to 8% each. In the digis
  the small out-of-time pulses appear 10 to 15 ns later than `25 ns x b`
  relative to the in-time pulse, so half the rise of crossing -1 falls into
  the in-time bucket. The time slew of the digitiser, up to 10 ns for
  charges of a few fC, is the parametrised effect of that size; it has not
  been isolated as the cause.

Out-of-time pile-up in HCAL is therefore a real part of the residual of
the attribution and of the neutral-hadron offset, larger than in ECAL, and
no in-time pile-up truth can assign it.

## 6. References

* ECAL multifit: CMS Collaboration, "Reconstruction of signal amplitudes in
  the CMS electromagnetic calorimeter in the presence of overlapping
  proton-proton interactions", JINST 15 (2020) P10002, arXiv:2006.14359.
* HCAL Phase-1 readout (SiPM, QIE11) and MAHI: CMS Collaboration,
  "Development of the CMS detector for the CERN LHC Run 3", JINST 19 (2024)
  P05064, arXiv:2309.05466; CMS DP-2018/018; CMS HCAL Phase-1 TDR,
  CERN-LHCC-2012-015.
* ECAL and HCAL readout: CMS Collaboration, "The CMS experiment at the CERN
  LHC", JINST 3 (2008) S08004.
* The pulse shapes themselves are not published: the HCAL ones are the
  formulas and tables of `HcalPulseShapes.cc`, the ECAL ones the conditions
  payloads below; `analysis/CaloPulses/dump_pulse_shapes.py` reads both.
* Code, CMSSW_15_0_4 (https://github.com/cms-sw/cmssw/tree/CMSSW_15_0_4):
  `CalibCalorimetry/HcalAlgos/src/HcalPulseShapes.cc`,
  `HcalTimeSlew.cc`; `SimCalorimetry/HcalSimAlgos/src/HcalSiPMHitResponse.cc`,
  `HcalTimeSlewSim.cc`; `SimCalorimetry/HcalSimProducers/python/hcalSimParameters_cfi.py`;
  `RecoLocalCalo/HcalRecAlgos/src/MahiFit.cc`;
  `RecoLocalCalo/HcalRecProducers/python/HBHEMahiParameters_cfi.py`;
  `SimCalorimetry/EcalSimAlgos/src/EcalShapeBase.cc`;
  `RecoLocalCalo/EcalRecAlgos/src/EcalUncalibRecHitMultiFitAlgo.cc`,
  `PulseChiSqSNNLS.cc`; `CalibCalorimetry/HcalPlugins/python/HcalTimeSlew_cff.py`.
* Conditions of `150X_mcRun3_2026_realistic_v4`: `EcalSimPulseShapePhaseI`,
  `EcalPulseShapes_mc`, `HcalMCParams_2019_v1.0_mc`,
  `HcalRecoParams_2021_v1.1_mc`.
