#!/usr/bin/env python3
# Usage: python3 export_xsecs_yaml.py -i datasets.txt -o data/xsecs.yaml -d ./genproductions_scripts/Utilities/calculateXSectionAndFilterEfficiency/ [--overwrite-all]
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
YAML_KEY_PATTERN = re.compile(r"^(?P<key>[^\s#][^:]*):\s*(?:#.*)?$")
YAML_FIELD_PATTERN = re.compile(
    r"^(?P<indent>\s+)(?P<field>xsec|uncertainty):\s*.*$"
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


def yaml_sections(lines):
    """Return top-level YAML key ranges for the generated xsec format."""
    sections, current_key, start = {}, None, None
    for index, line in enumerate(lines):
        match = YAML_KEY_PATTERN.match(line)
        if not match:
            continue
        if current_key is not None:
            sections[current_key] = (start, index)
        current_key, start = match["key"], index
    if current_key is not None:
        sections[current_key] = (start, len(lines))
    return sections


def confirm_overwrite(key, output):
    """Ask whether to replace an existing sample's xsec values."""
    while True:
        answer = input(
            f"Cross section for {key!r} exists in {output}. "
            "Overwrite xsec and uncertainty? [y/N]: "
        ).strip().lower()
        if answer in ("", "n", "no"):
            return False
        if answer in ("y", "yes"):
            return True
        print("Please answer yes or no.")


def update_cross_section(lines, start, end, xsec, uncertainty):
    """Replace only xsec and uncertainty fields in one YAML section."""
    values = {"xsec": xsec, "uncertainty": uncertainty}
    found = set()
    for index in range(start + 1, end):
        match = YAML_FIELD_PATTERN.match(lines[index])
        if match:
            field = match["field"]
            lines[index] = f"{match['indent']}{field}: {values[field]}\n"
            found.add(field)
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    for field in ("xsec", "uncertainty"):
        if field not in found:
            lines.insert(insert_at, f"  {field}: {values[field]}\n")
            insert_at += 1


def append_sample(lines, key, das, process, xsec, uncertainty):
    """Append a new sample in the established YAML layout."""
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.extend([
        f"{key}:\n",
        f'  das: "{das}"\n',
        f'  process: "{process}"\n',
        f"  xsec: {xsec}\n",
        f"  uncertainty: {uncertainty}\n",
        "\n",
    ])


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
    parser.add_argument("--overwrite-all", action="store_true",
                        help="replace existing xsec values without prompting")
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

    output = Path(args.output)
    lines = output.read_text().splitlines(keepends=True) if output.exists() else []
    for key, das, process, xsec, uncertainty in samples:
        sections = yaml_sections(lines)
        if key in sections:
            if args.overwrite_all or confirm_overwrite(key, output):
                update_cross_section(lines, *sections[key], xsec, uncertainty)
            continue
        append_sample(lines, key, das, process, xsec, uncertainty)
    output.write_text("".join(lines))
    print(f"Updated {len(samples)} samples in {output}")


if __name__ == "__main__":
    main()
