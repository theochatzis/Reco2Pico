#!/usr/bin/env python3
"""Utilities related to CMS DAS input discovery for Reco2Pico batch production."""

import json

from Reco2Pico.PicoProducer.utils.common import KILL, colored_text, command_output_lines, is_int


def load_dataset_data(das_name, max_files=-1, max_events=-1, parentFiles_levels=2, files_prefix='', verbose=False):
    """Return a JME-style dataset dictionary from DAS.

    The returned format is:
      {"DAS": <dataset>, "files": [{"file", "nevents", "parentFiles_1", "parentFiles_2"}, ...]}
    """
    if verbose:
        print(colored_text(das_name, ['1']))

    dataset_split = das_name.split('/')
    if len(dataset_split) != 4:
        KILL('load_dataset_data -- invalid data-set name (format is incorrect, check slashes): ' + str(das_name))

    dset_data = {'DAS': str(das_name), 'files': []}

    dataset_files = command_output_lines(
        'dasgoclient --query "file dataset=' + str(das_name) + ' | grep file.name,file.nevents"'
    )
    dataset_files = sorted(set(line for line in dataset_files if line))

    if not dataset_files:
        KILL('load_dataset_data -- empty list of input files for dataset: ' + str(das_name))

    if max_files > 0:
        dataset_files = dataset_files[:max_files]

    dataset_files_nevents = []
    for line in dataset_files:
        parts = line.split()
        if len(parts) != 2:
            KILL('load_dataset_data -- unexpected DAS output: ' + str(line))
        if not is_int(parts[1]):
            KILL('load_dataset_data -- invalid event count from DAS: ' + str(line))
        dataset_files_nevents.append([parts[0], int(parts[1])])

    tot_events, break_loop = 0, False
    for file_idx, (file_name, file_nevents) in enumerate(dataset_files_nevents):
        tot_events += file_nevents
        if (max_events > 0) and (tot_events >= max_events):
            break_loop = True

        if verbose:
            print('  [ file', file_idx + 1, '/', len(dataset_files_nevents), '] [ # events =', file_nevents, ']', file_name)

        parents1 = []
        parents2 = []
        if parentFiles_levels > 0:
            parents1 = command_output_lines('dasgoclient --query "parent file=' + str(file_name) + '"')
            parents1 = sorted(set(files_prefix + p for p in parents1 if p))

            if parentFiles_levels > 1:
                for parent in parents1:
                    parents2_tmp = command_output_lines('dasgoclient --query "parent file=' + str(parent) + '"')
                    parents2_tmp = [p.replace(' ', '') for p in parents2_tmp]
                    parents2 += [files_prefix + p for p in parents2_tmp if p]
                parents2 = sorted(set(parents2))

        if verbose:
            for parent in parents2:
                print(' ' * 5, parent)

        dset_data['files'].append({
            'file': files_prefix + file_name,
            'nevents': file_nevents,
            'parentFiles_1': parents1,
            'parentFiles_2': parents2,
        })

        if break_loop:
            break

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


def skim_das_jsondump(file_path, max_files=-1, max_events=-1, verbose=False):
    """Load and skim a JSON dump previously produced by bdriver."""
    with open(file_path) as handle:
        dset_data = json.load(handle)

    assert_dataset_data(dset_data, verbose=verbose)

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
