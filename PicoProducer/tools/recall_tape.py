#!/usr/bin/env python3
"""Recall CERN CMS EOS tape files for Reco2Pico.

Usage:
  ./tools/recall_tape.py FILE_LIST
  ./tools/recall_tape.py FILE_LIST --wait 21600
  ./tools/recall_tape.py --dataset /PRIMARY/PROCESSING/TIER --wait 21600
  ./tools/recall_tape.py FILE_LIST --dry-run
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def read_file_list(path):
    """Read non-empty, non-commented file names from a text file."""
    input_path = Path(path)
    if not input_path.is_file():
        raise SystemExit(f"ERROR: input file list does not exist: {path}")
    return [
        line.strip()
        for line in input_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def query_dataset(dataset):
    """Return the files belonging to a CMS DAS dataset."""
    dasgoclient = shutil.which("dasgoclient")
    if not dasgoclient:
        raise SystemExit("ERROR: dasgoclient is unavailable; run cmsenv first")

    query = f"file dataset={dataset}"
    try:
        result = subprocess.run(
            [dasgoclient, "--query", query],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or f"exit status {error.returncode}"
        raise SystemExit(f"ERROR: DAS query failed: {detail}") from error

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tape_url(file_name, endpoint):
    """Convert a CMS LFN or XRootD URL to its CERN EOS tape SURL."""
    file_name = file_name.strip()

    if "//store/" in file_name:
        file_name = "/store/" + file_name.split("//store/", 1)[1]

    if file_name.startswith("/store/"):
        eos_path = "/eos/cms" + file_name
    elif file_name.startswith("/eos/cms/store/"):
        eos_path = file_name
    else:
        raise ValueError(
            f"unsupported input {file_name!r}; expected /store/... or "
            "root://...//store/..."
        )

    return endpoint.rstrip("/") + "/" + eos_path


def unique(items):
    """Deduplicate while preserving input order."""
    return list(dict.fromkeys(items))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Recall Reco2Pico input files from CERN CMS EOS tape"
    )
    parser.add_argument("file_list", nargs="?", help="text file containing one input file per line")
    parser.add_argument("--dataset", help="CMS DAS dataset instead of a file list")
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        metavar="SECONDS",
        help="poll until files are online, or stop after this many seconds; default: submit only",
    )
    parser.add_argument(
        "--pin-lifetime",
        type=int,
        default=86400,
        metavar="SECONDS",
        help="requested disk pin lifetime; default: 86400",
    )
    parser.add_argument(
        "--endpoint",
        default="root://eoscms.cern.ch",
        help="EOS endpoint; default: root://eoscms.cern.ch",
    )
    parser.add_argument("--dry-run", action="store_true", help="print resolved SURLs without recalling")
    args = parser.parse_args()

    if bool(args.file_list) == bool(args.dataset):
        parser.error("specify exactly one of FILE_LIST or --dataset")
    if args.wait < 0 or args.pin_lifetime <= 0:
        parser.error("--wait must be non-negative and --pin-lifetime must be positive")
    return args


def main():
    args = parse_args()
    files = query_dataset(args.dataset) if args.dataset else read_file_list(args.file_list)
    if not files:
        raise SystemExit("ERROR: no input files were found")

    try:
        urls = unique(tape_url(file_name, args.endpoint) for file_name in files)
    except ValueError as error:
        raise SystemExit(f"ERROR: {error}") from error

    print(f"Resolved {len(urls)} unique CERN EOS file(s)")
    if args.dry_run:
        print("\n".join(urls))
        return 0

    bringonline = shutil.which("gfal-bringonline")
    if not bringonline:
        raise SystemExit("ERROR: gfal-bringonline is unavailable")

    # The CMSSW Python does not provide gfal2 on lxplus; select the system
    # interpreter used by the gfal utility without inspecting credentials.
    environment = os.environ.copy()
    if Path("/usr/bin/python3").is_file():
        environment["GFAL_PYTHONBIN"] = "/usr/bin/python3"

    with tempfile.NamedTemporaryFile(mode="w", prefix="reco2pico_recall_") as handle:
        handle.write("\n".join(urls) + "\n")
        handle.flush()
        command = [
            bringonline,
            "--from-file",
            handle.name,
            "--pin-lifetime",
            str(args.pin_lifetime),
            "--polling-timeout",
            str(args.wait),
            "--timeout",
            str(max(1800, args.wait + 60)),
        ]
        mode = "requesting and monitoring" if args.wait else "submitting"
        print(f"{mode.capitalize()} tape recall with gfal-bringonline")
        return subprocess.run(command, env=environment).returncode


if __name__ == "__main__":
    raise SystemExit(main())
