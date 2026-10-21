import hashlib
import json
import os
import sys

import FWCore.ParameterSet.Config as cms


def picoCommand():
    """
    The configuration and arguments of this cmsRun job, as a JSON string:
    {"config": path, "sha1": hash of its contents, "args": [...], "release": ...}.
    The path is relative to $CMSSW_BASE/src when the file is in it. Returns
    None outside cmsRun (cmsRun sets sys.argv to the configuration and its
    arguments).
    """
    cfg = sys.argv[0] if sys.argv else ""
    if not cfg.endswith("_cfg.py") or not os.path.isfile(cfg):
        return None
    path = os.path.realpath(cfg)
    with open(path, "rb") as f:
        sha1 = hashlib.sha1(f.read()).hexdigest()
    src = os.path.join(os.path.realpath(os.environ.get("CMSSW_BASE", "/")), "src") + os.sep
    if path.startswith(src):
        path = path[len(src):]
    return json.dumps(
        {"config": path, "sha1": sha1, "args": sys.argv[1:], "release": os.environ.get("CMSSW_VERSION", "")},
        separators=(",", ":"),
    )


def picoMetadata(process, strings=None):
    """
    Return process.nanoMetadata, creating it if needed, with strings added.

    NanoAODOutputModule writes every string made by the module labelled
    "nanoMetadata" as a TObjString in the Pico file. PicoMetadataProducer
    writes the constant strings given here plus "picoProvenance": which module
    wrote each table and what each of them read (see the plugin). The string
    "picoCommand" records the configuration and arguments of the job (see
    picoCommand), so that navigator/navigator.py can rebuild it from the file.

    It must run on every event to record the provenance, so put it on the
    Path that makes the tables, e.g.
        process.p = cms.Path(process.picoSequence + picoMetadata(process))
    The output module needs "keep nanoaodUniqueString_nanoMetadata_*_*".
    """
    if not hasattr(process, "nanoMetadata"):
        process.nanoMetadata = cms.EDProducer(
            "PicoMetadataProducer",
            strings=cms.PSet(tag=cms.string("Reco2Pico")),
            provenanceName=cms.string("picoProvenance"),
            tableLabels=cms.vstring("*Table"),
        )
        command = picoCommand()
        if command:
            process.nanoMetadata.strings.picoCommand = cms.string(command)
    for name, value in (strings or {}).items():
        setattr(process.nanoMetadata.strings, name, cms.string(value))
    return process.nanoMetadata
