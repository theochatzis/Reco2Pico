# TrueJES illustrations

TikZ figures of the study, for presentations and the note. `make` rebuilds
every figure (cropped single-figure PDFs through the `preview` package, no
`standalone` class needed on lxplus) and the summary document
`TrueJES_illustrations.pdf` that collects them with a short text each.

| figure | shows |
|---|---|
| `ladder.pdf` | the six steps from GenJet to the reconstructed jets, what each adds, and the response at each |
| `ancestry_matching.pdf` | the matching by Geant4 ancestry: gen jet, decay tree, sim jets, the shared energy and the two fractions |
| `terminal_rule.pdf` | which Geant4 particles are clustered: continuing particle with a delta ray, decay, particle born inside the calorimeter |
| `calo_deposits.pdf` | the per-particle calorimeter deposits from the sim hits (`SimCalo`) and the ideal particle flow (`SimPFCand`) |
| `reco_attribution.pdf` | PF candidates attributed to simulated particles and the reconstructed jets matched by the same ancestry; `signalPtRatio` |
| `pileup_attribution.pdf` | how the pile-up is removed: charged candidates through the track, neutral ones cell by cell with the cap, the signal part of the jet and the shared-energy variant |
| `pf_block.pdf` | the PF block tables: elements, stored links, elements used by the candidates |

`preamble.tex` holds the shared styles and the colour palette. Edit a figure,
run `make`, and include the PDF; `make clean` removes the LaTeX by-products.
