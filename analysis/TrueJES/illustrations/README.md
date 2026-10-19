# TrueJES illustrations

TikZ figures of the study, for presentations and the note. `make` rebuilds
every figure (cropped single-figure PDFs through the `preview` package, no
`standalone` class needed on lxplus) and the summary document
`TrueJES_illustrations.pdf` that collects them with a short text each.

| figure | shows |
|---|---|
| `ladder.pdf` | the six steps from GenJet to the reconstructed jets, what each adds, and the response at each |
| `ancestry_matching.pdf` | the matching by Geant4 ancestry: gen jet, decay tree, sim jets, the shared energy and the two fractions |
| `entrance_rule.pdf` | which Geant4 particles are clustered, the calorimeter-entrance particles: conversion in the tracker, decay inside the calorimeter, stored secondary without the crossing flag |
| `calo_deposits.pdf` | the per-particle calorimeter deposits from the sim hits (`SimCalo`) and the ideal particle flow (`SimPFCand`) |
| `reco_attribution.pdf` | PF candidates attributed to simulated particles and the reconstructed jets matched by the same ancestry; `signalPtRatio` |
| `attribution_samples.pdf` | the attribution on the premixed sample (signal cap, everything else unattributed in one number) next to the classically mixed one (pile-up shares, residual), and why the signal part is the same on both |
| `pileup_truth.pdf` | the classically mixed chain, what a cell looks like with the pile-up deposits known, and the three measurements of the pile-up of a jet |
| `attribution_chain.pdf` | from the jet down to the cell: candidates, block elements, clusters, rechits, and the cell where the rechit energy is attributed to the simulated particles (formula, residual), then back up to the jet |
| `pileup_attribution.pdf` | how the pile-up is removed: charged candidates through the track, neutral ones cell by cell with the cap, the signal part of the jet and the shared-energy variant |
| `pf_block.pdf` | the PF block tables: elements, stored links, elements used by the candidates |
| `build_figures.sh [FIGURE ...]` | `make` (every figure, or the named ones), a PNG of each (`pdftoppm`, `DPI` 110) and, for the figures the write-up embeds, a copy of the PDF and PNG into `docs/figures` |

`preamble.tex` holds the shared styles and the colour palette. Edit a figure,
run `make`, and include the PDF; `make clean` removes the LaTeX by-products.
