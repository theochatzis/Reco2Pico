#!/bin/bash
DIR=${PWD}
cd genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/
./calculateXSectionAndFilterEfficiency.sh -f datasets.txt -c Run3Winter25MiniAOD -d MINIAODSIM

cd ${DIR}

python3 export_xsecs_yaml.py -i datasets.txt -o data/xsecs.yaml -d ./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/

