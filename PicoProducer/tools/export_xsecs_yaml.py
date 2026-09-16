#!/usr/bin/env python3
# Usage: python3 export_xsecs_yaml.py -i datasets.txt -o data/xsecs.yaml -d ./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/
"""Export final GenXSecAnalyzer cross sections for listed datasets as YAML."""

import argparse
import re
from pathlib import Path
import os

XSEC_PATTERN = re.compile(
    r"After filter: final cross section = "
    r"(?P<xsec>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?) "
    r"\+- (?P<uncertainty>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?) pb"
)


def primary_dataset_name(dataset):
    """Return the primary-dataset component from a DAS dataset path."""
    parts = dataset.split("/")
    if len(parts) < 2 or not parts[1]:
        raise ValueError(f"invalid DAS dataset path: {dataset}")
    return parts[1]


def yaml_names(das):
    """Derive the YAML key and physics-process name from a DAS name."""
    process = re.split(r"_Tune", das, maxsplit=1)[0]
    energy = re.search(r"_(?P<energy>13(?:p6)?TeV)(?:_|$)", das)
    if not energy:
        raise ValueError(f"centre-of-mass energy not found in DAS name: {das}")
    key = f"{process}_{energy['energy']}"
    return key, process


def final_cross_section(log_path):
    """Extract final cross section and its statistical uncertainty in pb."""
    match = XSEC_PATTERN.search(log_path.read_text())
    if not match:
        raise ValueError("final cross section line not found")
    return float(match["xsec"]), float(match["uncertainty"])


def main():
    parser = argparse.ArgumentParser(
        description="Export GenXSecAnalyzer final cross sections to YAML."
    )
    parser.add_argument("-d", "--dir", default="./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/",
                        help="path to directory with datasets.txt and logs")
    parser.add_argument("-i", "--input", default="datasets.txt",
                        help="text file containing one DAS dataset path per line")
    parser.add_argument("-o", "--output", default="xsecs.yaml",
                        help="output YAML file")
    args = parser.parse_args()
    
    input = os.path.join(args.dir,args.input)
    datasets = [
        line.strip() for line in Path(input).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    errors, samples = [], []
    for dataset in datasets:
        try:
            das = primary_dataset_name(dataset)
            key, process = yaml_names(das)
            xsec, uncertainty = final_cross_section(Path(os.path.join(args.dir,f"xsec_{das}.log")))
            samples.append((key, das, process, xsec, uncertainty))
        except (OSError, ValueError) as error:
            errors.append(f"{dataset}: {error}")

    if errors:
        parser.error("could not export YAML:\n  " + "\n  ".join(errors))

    lines = []
    for key, das, process, xsec, uncertainty in samples:
        lines.extend([
            f"{key}:",
            f'  das: "{das}"',
            f'  process: "{process}"',
            f"  xsec: {xsec}",
            f"  uncertainty: {uncertainty}",
            "",
        ])
    Path(args.output).write_text("\n".join(lines))
    print(f"Wrote {len(samples)} samples to {args.output}")


if __name__ == "__main__":
    main()
