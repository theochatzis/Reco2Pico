# Reco2Pico releases

Each Reco2Pico release is a git tag `v<MAJOR>.<MINOR>.<PATCH>_<branch>` on one
release branch. This page lists the supported lines, what each supports, and
the release notes. How branches, tags and porting work is in
[branching.md](branching.md).

## Supported lines

| line | branch | CMSSW release | SCRAM_ARCH | era / conditions used | latest tag |
|---|---|---|---|---|---|
| Phase 2 | `main` | CMSSW_20_1_0_pre3 | el9_amd64_gcc14 | `Phase2C26I13M9`, geometry `ExtendedRun4D127`, `auto:phase2_realistic_T35` | [v1.0.0_CMSSW_20_1_X](notes/v1.0.0_CMSSW_20_1_X.md) |
| Run 3 | `CMSSW_15_0_X` | CMSSW_15_0_4 | el9_amd64_gcc12 | `Run3_2025`, `150X_mcRun3_2026_realistic_v4` (Winter26 DY), `auto:phase1_2025_realistic` (RECO_to_pico default) | [v1.0.0_CMSSW_15_0_X](notes/v1.0.0_CMSSW_15_0_X.md) |

Releases of one CMSSW cycle other than the one listed (e.g. a later
`CMSSW_15_0_<patch>`) should work but are not tested until listed here.

## Feature support

Status at the latest tag of each line:

- **used**: run in a production or study with this release;
- **builds**: compiles and its config loads, not yet run on events in this release;
- **n/a**: does not apply to this detector.

| feature | Phase 2 (`main`) | Run 3 (`CMSSW_15_0_X`) |
|---|---|---|
| `miniAOD_to_pico_cfg.py` | builds | builds |
| `AOD_to_pico_cfg.py` | builds | builds |
| `RECO_to_pico_cfg.py`, reco groups (`event`, `muons`, `electrons`, `jets`, `pfcands`, `tracks`, `vertices`, `pfclusters`, `rechits`, `pfblocks`) | builds | used |
| `genparts`, `sim` (SimTrack/SimJet/TP truth) | builds | used |
| `simcalo`, `recojets` (calorimeter and PF truth; ECAL + HCAL barrel/endcap cells) | builds; HGCAL not covered | used |
| `calodigis` (EB/EE/HBHE digis from RAW) | builds; HGCAL not covered | used |
| `pileupTruth` (classically mixed samples) | builds | used |
| workflow `samples_workflows/phase2_gun` (`hgcalval-nano`) | used | n/a |
| workflow `samples_workflows/run3_rawsim` | n/a | used |
| workflow `samples_workflows/run3_mix` | n/a | used |
| Condor tools (`bdriver`, `submit_bdriver_chain.sh`, `condor/`) | used | used |

When a release changes a status, update this table in the same commit as its
release note.

## Release notes

Newest first. One file per tag in [notes/](notes/), named after the tag.

| tag | date | line | summary |
|---|---|---|---|
| [v1.0.0_CMSSW_20_1_X](notes/v1.0.0_CMSSW_20_1_X.md) | 2026-10-19 | Phase 2 | first tagged release: same code as v1.0.0_CMSSW_15_0_X, built in CMSSW_20_1_0_pre3 |
| [v1.0.0_CMSSW_15_0_X](notes/v1.0.0_CMSSW_15_0_X.md) | 2026-10-19 | Run 3 | first tagged release: RECO truth tables, calo digis, pile-up truth, run3_rawsim and run3_mix workflows |

## Adding a release

1. Port what should be shared (see [branching.md](branching.md)), build, run the short test.
2. Copy [notes/TEMPLATE.md](notes/TEMPLATE.md) to `notes/<tag>.md` and fill it in.
3. Update the tables above (latest tag, feature support, release notes).
4. Commit, then tag and publish (commands in [branching.md](branching.md#making-a-release)).

Keep this directory identical on all branches: a note written on one branch is
cherry-picked to the others.
