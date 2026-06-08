#!/usr/bin/env python3
"""Common helper functions for Reco2Pico batch scripts."""

import os
import subprocess


def colored_text(txt, keys=None):
    keys = keys or []
    out = ''.join('\033[' + str(key) + 'm' for key in keys)
    out += str(txt)
    if keys:
        out += '\033[0m'
    return out


def KILL(log):
    raise RuntimeError('\n ' + colored_text('@@@ FATAL', ['1', '91']) + ' -- ' + str(log) + '\n')


def WARNING(log):
    print('\n ' + colored_text('@@@ WARNING', ['1', '93']) + ' -- ' + str(log) + '\n')


def MKDIRP(dirpath, verbose=False, dry_run=False):
    if verbose:
        print('\033[1m>\033[0m os.makedirs("' + str(dirpath) + '", exist_ok=True)')
    if dry_run:
        return
    os.makedirs(dirpath, exist_ok=True)


def EXE(cmd, suspend=True, verbose=False, dry_run=False):
    if verbose:
        print('\033[1m>\033[0m ' + str(cmd))
    if dry_run:
        return 0

    exitcode = os.system(cmd)
    exitcode = min(255, exitcode)

    if exitcode and suspend:
        raise RuntimeError(exitcode)

    return exitcode


def get_output(cmd, permissive=False):
    prc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = prc.communicate()

    if (not permissive) and prc.returncode:
        KILL('get_output -- shell command failed (execute command to reproduce the error):\n'
             + ' ' * 14 + '> ' + str(cmd) + '\n'
             + err.decode('utf-8', errors='replace'))

    return out, err


def command_output_lines(cmd, stdout=True, stderr=False, permissive=False):
    lines = []

    if not (stdout or stderr):
        WARNING('command_output_lines -- options "stdout" and "stderr" both set to FALSE, returning empty list')
        return lines

    out, err = get_output(cmd, permissive=permissive)
    if stdout:
        lines += out.decode('utf-8', errors='replace').split('\n')
    if stderr:
        lines += err.decode('utf-8', errors='replace').split('\n')

    return lines


def which(program, permissive=False, verbose=False):
    fpath, _ = os.path.split(program)
    matches = []

    if fpath:
        if os.path.isfile(program) and os.access(program, os.X_OK):
            matches.append(program)
    else:
        for path in os.environ.get('PATH', '').split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
                matches.append(exe_file)

    matches = sorted(set(matches))

    if not matches:
        msg = 'which -- executable not found: ' + str(program)
        if permissive:
            if verbose:
                WARNING(msg)
            return None
        KILL(msg)

    if len(matches) > 1 and verbose:
        WARNING('which -- executable "' + str(program) + '" has multiple matches:\n' + str(matches))

    return matches[0]


def is_int(value):
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def is_float(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
