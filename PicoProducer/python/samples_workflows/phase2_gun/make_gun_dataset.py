#!/usr/bin/env python3
"""
Write a bdriver dataset JSON for the particle-gun chain.

Each "file" is a virtual gun://jobNNN entry with `nevents` events; bdriver then
creates one job per entry (use -n EVENTS_PER_JOB with the same value), passes
inputFiles=gun://jobNNN to step 1, and gun_varparsing_tail.py turns NNN into
the random-seed / firstEvent / firstLuminosityBlock offsets.

    make_gun_dataset.py --name gun_pip_p1to200 --jobs 200 --events-per-job 500 -o datasets/gun_pip_p1to200.json
"""
import argparse
import json
import os
import sys


def build_dataset(name, jobs, events_per_job):
    width = max(3, len(str(jobs - 1)))
    return {
        'DAS': 'gun://' + name,
        'files': [
            {
                'file': 'gun://job{:0{w}d}'.format(job, w=width),
                'nevents': int(events_per_job),
                'parentFiles_1': [],
                'parentFiles_2': [],
            }
            for job in range(jobs)
        ],
    }


def _fallback_assert(dset):
    """Same checks as Reco2Pico.PicoProducer.utils.das.assert_dataset_data (used without cmsenv)."""
    assert isinstance(dset, dict), 'invalid content of dataset json'
    assert isinstance(dset.get('DAS'), str), 'missing/invalid DAS key'
    assert isinstance(dset.get('files'), list), 'missing/invalid files key'
    for entry in dset['files']:
        assert isinstance(entry, dict), 'invalid file entry'
        assert isinstance(entry.get('file'), str), 'missing/invalid file key'
        assert isinstance(entry.get('nevents'), int) and entry['nevents'] >= 0, 'missing/invalid nevents'
        for key in ('parentFiles_1', 'parentFiles_2'):
            assert isinstance(entry.get(key), list), 'missing/invalid ' + key
            assert all(isinstance(v, str) for v in entry[key]), 'invalid parent file entry'


def validate(dset):
    try:
        from Reco2Pico.PicoProducer.utils.das import assert_dataset_data
    except ImportError:
        sys.stderr.write('[make_gun_dataset] warning: Reco2Pico not importable (no cmsenv?); using built-in validation\n')
        _fallback_assert(dset)
        return
    assert_dataset_data(dset)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--name', required=True, help='dataset label; written as "DAS": "gun://NAME"')
    parser.add_argument('--jobs', type=int, required=True, help='number of jobs (= number of gun://jobNNN entries)')
    parser.add_argument('--events-per-job', type=int, required=True, help='events per job (nevents of each entry)')
    parser.add_argument('-o', '--output', required=True, help='output JSON path')
    args = parser.parse_args(argv)

    if args.jobs <= 0:
        parser.error('--jobs must be positive')
    if args.events_per_job <= 0:
        parser.error('--events-per-job must be positive')

    dset = build_dataset(args.name, args.jobs, args.events_per_job)
    validate(dset)

    outdir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(outdir, exist_ok=True)
    with open(args.output, 'w') as handle:
        json.dump(dset, handle, indent=2)
        handle.write('\n')
    print('[make_gun_dataset] {}: {} jobs x {} events -> {}'.format(
        dset['DAS'], args.jobs, args.events_per_job, args.output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
