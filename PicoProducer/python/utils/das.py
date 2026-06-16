#!/usr/bin/env python3
"""Utilities related to CMS DAS input discovery for Reco2Pico batch production."""

import json
import shlex
import sys
import time

from Reco2Pico.PicoProducer.utils.common import KILL, colored_text, command_output_lines, is_int


def _das_command(query, json_output=False):
    flag = ' --json' if json_output else ''
    return 'dasgoclient' + flag + ' --query ' + shlex.quote(str(query))


def _das_lines(query, json_output=False):
    return command_output_lines(_das_command(query, json_output=json_output))


def _progress_bar(label, current, total, detail='', enabled=True):
    """Small stderr progress bar that works on lxplus and in batch logs."""
    if not enabled:
        return
    total = max(int(total), 1)
    current = min(max(int(current), 0), total)
    width = 28
    filled = int(width * float(current) / float(total))
    bar = '#' * filled + '-' * (width - filled)
    msg = '\r{:<28s} [{}] {:>4d}/{:<4d}'.format(label, bar, current, total)
    if detail:
        msg += '  ' + str(detail)
    sys.stderr.write(msg)
    if current >= total:
        sys.stderr.write('\n')
    sys.stderr.flush()


def _load_lumi_mask(lumi_json):
    """Return a dict {run: [(first_lumi, last_lumi), ...]} from a CMS Golden JSON."""
    if lumi_json is None:
        return None

    with open(lumi_json) as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        KILL('load_lumi_mask -- invalid lumi-mask JSON: top-level object must be a dictionary')

    mask = {}
    for run, ranges in raw.items():
        try:
            run_int = int(run)
        except (TypeError, ValueError):
            KILL('load_lumi_mask -- invalid run number in lumi-mask JSON: ' + str(run))

        if not isinstance(ranges, list):
            KILL('load_lumi_mask -- invalid lumi ranges for run ' + str(run))

        parsed_ranges = []
        for item in ranges:
            if (not isinstance(item, list)) or len(item) != 2:
                KILL('load_lumi_mask -- invalid lumi range for run ' + str(run) + ': ' + str(item))
            try:
                first, last = int(item[0]), int(item[1])
            except (TypeError, ValueError):
                KILL('load_lumi_mask -- invalid lumi range for run ' + str(run) + ': ' + str(item))
            if first <= 0 or last < first:
                KILL('load_lumi_mask -- invalid lumi range for run ' + str(run) + ': ' + str(item))
            parsed_ranges.append((first, last))

        if parsed_ranges:
            mask[run_int] = parsed_ranges

    if not mask:
        KILL('load_lumi_mask -- lumi-mask JSON contains no valid run/lumi ranges: ' + str(lumi_json))

    return mask


def _normalise_das_file_name(file_name):
    """Convert root://...//store/... or file:/store/... to the DAS /store/... name."""
    file_name = str(file_name)
    if file_name.startswith('file:'):
        file_name = file_name[5:]
    marker = '//store/'
    if marker in file_name:
        return '/store/' + file_name.split(marker, 1)[1]
    marker = '/store/'
    if marker in file_name:
        return '/store/' + file_name.split(marker, 1)[1]
    return file_name


def _parse_file_nevents_lines(lines, context):
    out = []
    for line in sorted(set(line for line in lines if line)):
        parts = line.split()
        if len(parts) != 2:
            KILL('load_dataset_data -- unexpected DAS output for ' + str(context) + ': ' + str(line))
        if not is_int(parts[1]):
            KILL('load_dataset_data -- invalid event count from DAS for ' + str(context) + ': ' + str(line))
        out.append([parts[0], int(parts[1])])
    return out


def _query_dataset_files_nevents(das_name):
    return _parse_file_nevents_lines(
        _das_lines('file dataset=' + str(das_name) + ' | grep file.name,file.nevents'),
        'dataset ' + str(das_name),
    )


def _query_dataset_runs(das_name):
    runs = []
    for line in _das_lines('run dataset=' + str(das_name)):
        line = line.strip()
        if not line:
            continue
        if not is_int(line):
            KILL('load_dataset_data -- invalid run number from DAS: ' + str(line))
        runs.append(int(line))
    return sorted(set(runs))


def _query_run_files_nevents(das_name, run):
    """Return [[file, nevents], ...] for one run.

    The first query asks DAS for file.name and file.nevents in one call.  If a
    DAS instance returns only file names for that query, the caller can fall
    back to the dataset-level file->nevents map.
    """
    query = 'file run=' + str(int(run)) + ' dataset=' + str(das_name) + ' | grep file.name,file.nevents'
    lines = sorted(set(line for line in _das_lines(query) if line))
    entries = []
    file_names_only = []
    for line in lines:
        parts = line.split()
        if len(parts) == 2 and is_int(parts[1]):
            entries.append([parts[0], int(parts[1])])
        elif len(parts) == 1:
            file_names_only.append(parts[0])
        else:
            # Fallback below: some DAS deployments may not support this grep combination.
            entries = []
            file_names_only = []
            break

    if entries:
        return entries

    query = 'file run=' + str(int(run)) + ' dataset=' + str(das_name)
    file_names = sorted(set(line.strip() for line in _das_lines(query) if line.strip()))
    return [[file_name, None] for file_name in file_names]


def _fill_missing_nevents(entries, das_name):
    if not any(nevents is None for _, nevents in entries):
        return entries

    all_files = _query_dataset_files_nevents(das_name)
    nevents_by_file = {name: nevents for name, nevents in all_files}
    filled = []
    missing = []
    for file_name, nevents in entries:
        if nevents is None:
            nevents = nevents_by_file.get(file_name)
        if nevents is None:
            missing.append(file_name)
        else:
            filled.append([file_name, int(nevents)])

    if missing:
        KILL('load_dataset_data -- could not determine nevents for DAS files:\n  ' + '\n  '.join(missing[:20]))
    return filled


def _as_int_list(value):
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        try:
            return [int(value)]
        except ValueError:
            return []
    if isinstance(value, list):
        out = []
        for item in value:
            out += _as_int_list(item)
        return out
    return []


def _as_lumi_ranges(value):
    """Convert DAS lumi payload fragments to [(first,last), ...]."""
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [(value, value)]
    if isinstance(value, str):
        try:
            lumi = int(value)
            return [(lumi, lumi)]
        except ValueError:
            return []
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in value):
            first, last = value
            return [(min(first, last), max(first, last))]
        out = []
        for item in value:
            out += _as_lumi_ranges(item)
        return out
    return []


def _extract_run_lumi_ranges(obj):
    """Recursively extract {run: [(first,last), ...]} from DAS JSON output."""
    out = {}

    if isinstance(obj, list):
        for item in obj:
            sub = _extract_run_lumi_ranges(item)
            for run, ranges in sub.items():
                out.setdefault(run, []).extend(ranges)
        return out

    if not isinstance(obj, dict):
        return out

    run_value = None
    for key in ('run_number', 'run', 'run_num'):
        if key in obj:
            run_value = obj[key]
            break

    lumi_value = None
    for key in ('lumi_section_num', 'lumi_section', 'lumis', 'lumi'):
        if key in obj:
            lumi_value = obj[key]
            break

    runs = _as_int_list(run_value)
    lumi_ranges = _as_lumi_ranges(lumi_value)
    if runs and lumi_ranges:
        for run in runs:
            out.setdefault(run, []).extend(lumi_ranges)

    for value in obj.values():
        sub = _extract_run_lumi_ranges(value)
        for run, ranges in sub.items():
            out.setdefault(run, []).extend(ranges)

    return out


def _query_file_lumis(file_name):
    """Query DAS for the run/lumi content of a file and return {run: [(first,last), ...]}."""
    das_file = _normalise_das_file_name(file_name)
    payload = '\n'.join(_das_lines('lumi file=' + das_file, json_output=True))

    try:
        decoded = json.loads(payload)
    except Exception as err:
        KILL('query_file_lumis -- failed to parse DAS JSON output for file: ' + str(das_file)
             + '\nerror: ' + str(err)
             + '\noutput: ' + payload[:2000])

    return _extract_run_lumi_ranges(decoded)


def _ranges_overlap(ranges_a, ranges_b):
    for a_first, a_last in ranges_a:
        for b_first, b_last in ranges_b:
            if a_first <= b_last and b_first <= a_last:
                return True
    return False


def _file_overlaps_lumi_mask(file_name, lumi_mask):
    """Return True when the DAS file has at least one run/lumi overlapping the mask."""
    if lumi_mask is None:
        return True

    file_lumis = _query_file_lumis(file_name)
    for run, file_ranges in file_lumis.items():
        if run not in lumi_mask:
            continue
        if _ranges_overlap(file_ranges, lumi_mask[run]):
            return True
    return False


def _apply_lumi_mask_to_file_entries(file_entries, lumi_json=None, verbose=False, progress=True):
    """Slow but precise fallback: query each file's lumi content and keep overlaps."""
    lumi_mask = _load_lumi_mask(lumi_json)
    if lumi_mask is None:
        return file_entries

    filtered = []
    total = len(file_entries)
    for idx, entry in enumerate(file_entries, start=1):
        file_name = entry['file'] if isinstance(entry, dict) else entry[0]
        _progress_bar('lumi-mask file scan', idx, total, file_name.split('/')[-1], enabled=progress)
        if _file_overlaps_lumi_mask(file_name, lumi_mask):
            filtered.append(entry)
            if verbose:
                print('  ' + colored_text('[lumi-mask keep]', ['92']), file_name)
        elif verbose:
            print('  ' + colored_text('[lumi-mask skip]', ['93']), file_name)

    if not filtered:
        KILL('apply_lumi_mask -- all input files were rejected by the lumi mask: ' + str(lumi_json))

    if verbose:
        print(colored_text('lumi-mask selected files:', ['1', '92']), str(len(filtered)) + '/' + str(len(file_entries)))

    return filtered


def _select_dataset_files_by_lumi_mask_runs(das_name, lumi_json, max_files=-1, max_events=-1,
                                            verbose=False, progress=True):
    """Fast DAS preselection.

    Strategy:
      1. query runs in dataset;
      2. intersect dataset runs with Golden JSON runs;
      3. query files only for those runs;
      4. stop querying more runs once max_files or max_events is already enough.

    This is run-level preselection.  The bdriver should still pass the lumi mask
    to cmsRun, because a selected file can contain both good and bad lumis.
    """
    lumi_mask = _load_lumi_mask(lumi_json)
    if lumi_mask is None:
        return None, None

    mask_runs = sorted(lumi_mask.keys())
    dataset_runs = _query_dataset_runs(das_name)
    selected_runs = sorted(set(dataset_runs).intersection(mask_runs))
    rejected_runs = sorted(set(dataset_runs).difference(mask_runs))

    report = {
        'lumi_json': str(lumi_json),
        'selection_mode': 'dataset-run-intersection',
        'dataset_runs': dataset_runs,
        'lumi_mask_runs': mask_runs,
        'selected_runs': selected_runs,
        'rejected_runs': rejected_runs,
        'stopped_early': False,
        'stop_reason': None,
        'runs': {},
        'selected_files': 0,
        'selected_events': 0,
    }

    if verbose:
        print(colored_text('lumi-mask dataset runs:', ['1']), len(dataset_runs))
        print(colored_text('lumi-mask JSON runs:', ['1']), len(mask_runs))
        print(colored_text('lumi-mask selected runs:', ['1', '92']), len(selected_runs))

    if not selected_runs:
        KILL('load_dataset_data -- no dataset runs are present in the lumi mask: ' + str(lumi_json))

    selected_entries = []
    seen_files = set()
    total_events = 0

    for idx, run in enumerate(selected_runs, start=1):
        _progress_bar('DAS files by good run', idx, len(selected_runs), 'run ' + str(run), enabled=progress)
        run_entries = _query_run_files_nevents(das_name, run)
        run_entries = _fill_missing_nevents(run_entries, das_name)
        run_entries = sorted(run_entries, key=lambda item: item[0])

        kept_files_this_run = []
        kept_events_this_run = 0
        for file_name, nevents in run_entries:
            if file_name in seen_files:
                continue
            seen_files.add(file_name)
            selected_entries.append([file_name, int(nevents)])
            kept_files_this_run.append(file_name)
            kept_events_this_run += int(nevents)
            total_events += int(nevents)

            if max_files > 0 and len(selected_entries) >= max_files:
                report['stopped_early'] = True
                report['stop_reason'] = 'max_files'
                break
            if max_events > 0 and total_events >= max_events:
                report['stopped_early'] = True
                report['stop_reason'] = 'max_events'
                break

        report['runs'][str(run)] = {
            'candidate_files_from_das': len(run_entries),
            'selected_files': len(kept_files_this_run),
            'selected_events': kept_events_this_run,
            'files': kept_files_this_run,
        }

        if report['stopped_early']:
            break

    if not selected_entries:
        KILL('load_dataset_data -- lumi-mask run preselection selected zero files: ' + str(lumi_json))

    report['selected_files'] = len(selected_entries)
    report['selected_events'] = total_events

    if verbose:
        print(colored_text('lumi-mask selected files:', ['1', '92']), len(selected_entries))
        print(colored_text('lumi-mask selected events (file-level):', ['1', '92']), total_events)
        if report['stopped_early']:
            print(colored_text('lumi-mask stopped early:', ['1', '93']), report['stop_reason'])

    return selected_entries, report


def _apply_limits_to_file_entries(file_entries, max_files=-1, max_events=-1):
    if max_files > 0:
        file_entries = file_entries[:max_files]

    if max_events > 0:
        last_index, tot_events = 0, 0
        for _, nevents in file_entries:
            last_index += 1
            tot_events += int(nevents)
            if tot_events >= max_events:
                break
        if last_index != len(file_entries):
            file_entries = file_entries[:last_index]

    return file_entries


def load_dataset_data(das_name, max_files=-1, max_events=-1, parentFiles_levels=2, files_prefix='',
                      lumi_json=None, verbose=False):
    """Return a JME-style dataset dictionary from DAS.

    The returned format is:
      {"DAS": <dataset>, "files": [{"file", "nevents", "parentFiles_1", "parentFiles_2"}, ...]}

    If lumi_json is provided, files are preselected with a fast run-level DAS
    strategy: dataset runs are intersected with Golden JSON runs, then only
    files belonging to selected runs are queried.  This avoids creating jobs for
    files whose runs are absent from the mask.  The cmsRun lumi mask should still
    be applied to drop bad lumis inside selected files.
    """
    if verbose:
        print(colored_text(das_name, ['1']))

    dataset_split = das_name.split('/')
    if len(dataset_split) != 4:
        KILL('load_dataset_data -- invalid data-set name (format is incorrect, check slashes): ' + str(das_name))

    dset_data = {'DAS': str(das_name), 'files': []}

    lumi_report = None
    if lumi_json is not None:
        dataset_files_nevents, lumi_report = _select_dataset_files_by_lumi_mask_runs(
            das_name=das_name,
            lumi_json=lumi_json,
            max_files=max_files,
            max_events=max_events,
            verbose=verbose,
            progress=True,
        )
    else:
        dataset_files_nevents = _query_dataset_files_nevents(das_name)
        if not dataset_files_nevents:
            KILL('load_dataset_data -- empty list of input files for dataset: ' + str(das_name))
        dataset_files_nevents = _apply_limits_to_file_entries(dataset_files_nevents, max_files=max_files, max_events=max_events)

    if not dataset_files_nevents:
        KILL('load_dataset_data -- empty list of input files for dataset: ' + str(das_name))

    for file_idx, (file_name, file_nevents) in enumerate(dataset_files_nevents):
        if verbose:
            print('  [ file', file_idx + 1, '/', len(dataset_files_nevents), '] [ # events =', file_nevents, ']', file_name)

        parents1 = []
        parents2 = []
        if parentFiles_levels > 0:
            parents1 = command_output_lines('dasgoclient --query ' + shlex.quote('parent file=' + str(file_name)))
            parents1 = sorted(set(files_prefix + p for p in parents1 if p))

            if parentFiles_levels > 1:
                for parent in parents1:
                    parents2_tmp = command_output_lines('dasgoclient --query ' + shlex.quote('parent file=' + str(parent)))
                    parents2_tmp = [p.replace(' ', '') for p in parents2_tmp]
                    parents2 += [files_prefix + p for p in parents2_tmp if p]
                parents2 = sorted(set(parents2))

        dset_data['files'].append({
            'file': files_prefix + file_name,
            'nevents': int(file_nevents),
            'parentFiles_1': parents1,
            'parentFiles_2': parents2,
        })

    if lumi_report is not None:
        dset_data['lumiMaskReport'] = lumi_report

    assert_dataset_data(dset_data=dset_data, verbose=verbose)
    return dset_data


def assert_dataset_data(dset_data, verbose=False):
    if not isinstance(dset_data, dict):
        KILL('assert_dataset_data -- invalid content of dataset json')

    if 'DAS' not in dset_data or not isinstance(dset_data['DAS'], str):
        KILL('assert_dataset_data -- missing/invalid DAS key')

    if 'files' not in dset_data or not isinstance(dset_data['files'], list):
        KILL('assert_dataset_data -- missing/invalid files key')

    for entry in dset_data['files']:
        if not isinstance(entry, dict):
            KILL('assert_dataset_data -- invalid file entry: ' + str(entry))

        if 'file' not in entry or not isinstance(entry['file'], str):
            KILL('assert_dataset_data -- missing/invalid file key: ' + str(entry))

        if 'nevents' not in entry or not isinstance(entry['nevents'], int) or entry['nevents'] < 0:
            KILL('assert_dataset_data -- missing/invalid nevents key: ' + str(entry))

        for key in ['parentFiles_1', 'parentFiles_2']:
            if key not in entry or not isinstance(entry[key], list):
                KILL('assert_dataset_data -- missing/invalid ' + key + ': ' + str(entry))
            for value in entry[key]:
                if not isinstance(value, str):
                    KILL('assert_dataset_data -- invalid parent file entry: ' + str(entry))


def skim_das_jsondump(file_path, max_files=-1, max_events=-1, lumi_json=None, verbose=False):
    """Load and skim a JSON dump previously produced by bdriver."""
    with open(file_path) as handle:
        dset_data = json.load(handle)

    assert_dataset_data(dset_data, verbose=verbose)

    if lumi_json is not None:
        # JSON dumps may not have enough dataset/run metadata for the fast run query.
        # Use the precise per-file DAS lumi check as a safe fallback.
        dset_data['files'] = _apply_lumi_mask_to_file_entries(
            dset_data['files'], lumi_json=lumi_json, verbose=verbose, progress=True)

    if max_files > 0:
        dset_data['files'] = dset_data['files'][:max_files]

    if max_events > 0:
        last_index, tot_events = 0, 0
        for entry in dset_data['files']:
            last_index += 1
            tot_events += entry['nevents']
            if tot_events >= max_events:
                break
        if last_index != len(dset_data['files']):
            dset_data['files'] = dset_data['files'][:last_index]

    return dset_data
