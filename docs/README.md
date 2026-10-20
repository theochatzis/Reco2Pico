# Reco2Pico physics notes

Write-ups of the studies done with the Reco2Pico Picos. They collect the
definitions, the reasoning behind them and the results, so that the plots can
be read without the code.

| note | study |
|---|---|
| [TrueJES.md](TrueJES.md) | the jet energy scale decomposed along the truth ladder: generator, the calorimeter-entrance particles (production momenta and at the face), calorimeter deposits per particle and per cell, ideal particle flow, reconstruction and pile-up; section 1.1 defines every jet in detail, section 5 the pile-up truth of the classically mixed chain |
| [TruthGraph.md](TruthGraph.md) | the CMSSW MC-truth graph (`PhysicsTools/TruthInfo`, cmssw#51829): levels, branches and adaptive reco-to-truth association, how it maps onto our calorimeter-entrance construction, the Run-3 simulation settings it does not have (boundary saving, reconnected ancestors, hence our orphan handling), and the ideas taken from it |
| [CaloPulses.md](CaloPulses.md) | from the simulated deposit to the rechit, one cell at a time: the ECAL and HCAL pulse shapes, front ends and pulse fits (multifit, MAHI) as the Run-3 simulation and reconstruction parametrise them, what the Picos carry on both sides (digis, deposits per crossing, templates) and what the cell figures show |

Technical documentation (tables, workflows, producers) stays next to the code:
`PicoProducer/README.md`, `PicoProducer/plugins/README.md`,
`PicoProducer/python/samples_workflows/`.
