# Tools
Here tools are stored that are useful for analysis. 

## xsec instructions
To derive XSections use the tools from `genproductions_scripts`:
```bash
git clone ssh://git@gitlab.cern.ch:7999/cms-gen/genproductions_scripts.git
```

Then use the scripts from `Utilities` and especially `compute_cross_section.py`. There is a helper script of our package to convert the logs into YAML file with all xsecs in a nice format.

First run the GenXSexAnalyzer with the helper tool:
```bash
cd genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/
./calculateXSectionAndFilterEfficiency.sh
```
this uses as input the datasets.txt located in the same directory for samples you want to probe.
Note that you need to specify the correct campaign, datatier and/or MCM etc. Default parameters in this are:
```
FILE='datasets.txt'
CAMPAIGN='RunIII2024Summer24MiniAODv6'
DATATIER='MINIAODSIM'
EVENTS='1000000'
MCM=False
SKIPEXISTING=False
```
Also the EVENTS if you need higher precision can also help. Check the cross section uncertainty in the end.

An example:
```bash
./calculateXSectionAndFilterEfficiency.sh -f datasets.txt -c Run3Winter25MiniAOD -d MINIAODSIM
```

Then it will produce logs of form xsec_(process_name).log e.g.
```
xsec_QCD-4Jets_Bin-HT-1000to1200_TuneCP5_13p6TeV_madgraphMLM-pythia8.log
xsec_QCD-4Jets_Bin-HT-100to200_TuneCP5_13p6TeV_madgraphMLM-pythia8.log
```
You can convert the output logs into a YAML file with the processes and the xsec using the `export_xsecs_yaml.py`.
```
python3 export_xsecs_yaml.py -i datasets.txt -o data/xsecs.yaml -d ./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/
```

Note that there is the MCM campaign (usually for centrally produced samples) you can do it and set the mcm to `True` in the `calculateXSectionAndFilterEfficiency.sh`. See section bellow `Info: McM — Monte Carlo Management`

## pileup
Tools for estimating the pileup distribution from MC files.

## Rucio replication rules

Use Rucio when the goal is a managed dataset replica at another CMS site.
Rucio handles any required source-side tape staging, so a separate manual tape
recall is normally unnecessary.

List rules for the default account or a dataset:

```bash
./tools/rucio_rules.sh list
./tools/rucio_rules.sh list /PRIMARY/PROCESSING/TIER
```

Request one complete copy at `T2_FI_HIP` for 180 days:

```bash
./tools/rucio_rules.sh add /PRIMARY/PROCESSING/TIER
```

Request a fraction of the files—for example, 10% for 30 days:

```bash
./tools/rucio_rules.sh --lifetime-days 30 \
  add-fraction /PRIMARY/PROCESSING/TIER 0.10
```

For example:

```bash
DATASET="/QCD_Bin-PT-15to7000_Par-PT-flat2022_TuneCP5_13p6TeV_pythia8/Run3Winter25Digi-142X_mcRun3_2025_realistic_v9-v4/GEN-SIM-RAW"

./tools/rucio_rules.sh --lifetime-days 30 \
  add-fraction "$DATASET" 0.10
```

The fractional command sorts the source file DIDs and selects
`ceil(number_of_files × fraction)` files. It creates a timestamped dataset in
the `user.$RUCIO_ACCOUNT` scope, attaches the selected files, and requests one
replica of that subset at `T2_FI_HIP`. It does not alter the original dataset.

Request one copy at any currently usable CRAB T1/T2 site:

```bash
./tools/rucio_rules.sh add-auto /PRIMARY/PROCESSING/TIER
```

The replication commands request approval and keep all selected files at one
site. Override defaults with `RUCIO_ACCOUNT`, `RUCIO_TARGET_RSE`, or
`RUCIO_LIFETIME`; alternatively, pass `--lifetime-days DAYS`.

Delete a rule by its ID:

```bash
./tools/rucio_rules.sh delete RULE_ID
```

Deletion asks for confirmation and removes the replication rule, not the
original CMS dataset.

## CERN tape recall

Recall the `/store/...` files in a Reco2Pico input list using `recall_tape.py`.
Current supported inputs are:
```bash
# Many files from one text file
./tools/recall_tape.py files.txt --wait 21600

# One DAS dataset
./tools/recall_tape.py --dataset /PRIMARY/PROCESSING/TIER --wait 21600

files, then issues one recall request.
```

For example:

```bash
./tools/recall_tape.py data/tape_recall_files.txt --wait 21600
```

The text file may contain many file paths, one `/store/...root` path per line.
It must not contain DAS dataset names.


Alternatively, resolve the file list directly from DAS:

```bash
./tools/recall_tape.py \
  --dataset /PRIMARY/PROCESSING/MINIAODSIM \
  --wait 21600
```

Only one DAS dataset can be supplied with `--dataset` per invocation. Multiple
DAS datasets in a text file are not currently supported.

Omit `--wait` to submit the recall without blocking. Use `--dry-run` to inspect
the resolved CERN EOS URLs. This utility targets files available in the CERN
CMS EOS namespace; remote tape replicas should be recalled through their owning
site or CMS data-management tools.




## Extra Infos
### Info: McM — Monte Carlo Management

McM (Monte Carlo Management) is the CMS system used to manage and track centrally produced Monte Carlo (MC) samples.

It provides information about CMS MC production requests, including:

Dataset and production request information

Cross sections

Generator configurations

Filter efficiencies

Number of requested/generated events

CMSSW releases and production conditions

Links between the different steps of the production chain

Production status and bookkeeping information

A sample is typically associated with a unique PrepID, for example:

HIG-Run3Summer23wmLHEGS-00042

The PrepID can be used to identify the corresponding production request in McM and retrieve its metadata.

Cross sections

For centrally produced CMS samples, McM is a useful source for obtaining the cross section associated with the exact production request.

For an analysis, the MC normalization is typically

[
w_{\mathrm{norm}} =
\frac{\mathcal{L},\sigma}{\sum_i w_i},
]

where:

(\mathcal{L}) is the integrated luminosity,

(\sigma) is the process cross section,

(\sum_i w_i) is the sum of generator weights of the processed events.

If a generator-level filter is applied and the quoted cross section is defined before filtering, the corresponding filter efficiency must also be included:

[
w_{\mathrm{norm}} =
\frac{\mathcal{L},\sigma,\epsilon_{\mathrm{filter}}}
{\sum_i w_i}.
]

Care should therefore be taken to understand exactly what the cross-section value stored in McM represents. For some analyses, an official higher-order theoretical cross section may be used instead of the generator-level value recorded during MC production.

In Reco2Pico

McM metadata can be used when building the sample bookkeeping information, while quantities specific to the actually processed events, such as genEventSumw, are stored in the PicoAOD Runs tree.

This separates:

McM / theory     → process cross section and production metadata
PicoAOD Runs     → sum of weights for the events actually processed

Together, these provide the information needed for MC normalization.
