#!/usr/bin/env python3
import argparse
import shutil
import subprocess
from pathlib import Path


def read_dataset(path):
    return [x.strip() for x in Path(path).read_text().splitlines() if x.strip() and not x.strip().startswith("#")]


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    parser = argparse.ArgumentParser(description="Submit Reco2Pico production jobs to Condor")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--cfg", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--files-per-job", type=int, default=1)
    parser.add_argument("--tables", default="event,muons,electrons,jets,met,custom_objects")
    parser.add_argument("--global-tag", default="auto:run2_mc")
    parser.add_argument("--max-events", default="-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = read_dataset(args.dataset)
    if not files:
        raise SystemExit(f"No input files found in {args.dataset}")

    repo_dir = Path(__file__).resolve().parents[1]
    work = repo_dir / "condor" / "work" / args.tag
    lists = work / "input_lists"
    logs = work / "logs"
    lists.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    job_inputs = []
    for idx, group in enumerate(chunks(files, args.files_per_job)):
        p = lists / f"input_{idx:05d}.txt"
        p.write_text("\n".join(group) + "\n")
        job_inputs.append(p)

    job_list_path = work / "job_inputs.txt"
    job_list_path.write_text("\n".join(str(p) for p in job_inputs) + "\n")

    wrapper_dst = work / "pico_job.sh"
    shutil.copy2(repo_dir / "condor" / "templates" / "pico_job.sh", wrapper_dst)
    wrapper_dst.chmod(0o755)

    sub_text = (repo_dir / "condor" / "templates" / "pico.sub").read_text()
    for key, value in {
        "JOB_WRAPPER": str(wrapper_dst),
        "JOB_LIST": str(job_list_path),
        "CFG": args.cfg,
        "OUTPUT_DIR": args.output_dir,
        "TABLES": args.tables,
        "GLOBAL_TAG": args.global_tag,
        "MAX_EVENTS": str(args.max_events),
    }.items():
        sub_text = sub_text.replace(key, value)

    sub_path = work / "pico.sub"
    sub_path.write_text(sub_text)
    print(f"Prepared {len(job_inputs)} jobs in {work}")
    print(f"Submit file: {sub_path}")

    if args.dry_run:
        print("Dry run only; not submitting.")
        return
    subprocess.run(["condor_submit", str(sub_path)], check=True)


if __name__ == "__main__":
    main()
