# Tools

Here tools are stored that are useful for analysis. 

## pileup
Tools for estimating the pileup distribution from MC files.

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

Then it will produce logs of form xsec_(process_name).log e.g.
```
xsec_QCD-4Jets_Bin-HT-1000to1200_TuneCP5_13p6TeV_madgraphMLM-pythia8.log
xsec_QCD-4Jets_Bin-HT-100to200_TuneCP5_13p6TeV_madgraphMLM-pythia8.log
```
You can convert the output logs into a YAML file with the processes and the xsec using the `export_xsecs_yaml.py`.
```
python3 export_xsecs_yaml.py -i datasets.txt -o data/xsecs.yaml -d ./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/
```



