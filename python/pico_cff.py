import FWCore.ParameterSet.Config as cms

from Reco2Pico.tables.event_cff import picoEventTables
from Reco2Pico.tables.muons_cff import picoMuonTables
from Reco2Pico.tables.electrons_cff import picoElectronTables
from Reco2Pico.tables.jets_cff import picoJetTables
from Reco2Pico.tables.met_cff import picoMetTables
from Reco2Pico.tables.custom_objects_cff import picoCustomObjectTables


def buildPicoSequence(process, enabled_tables=None):
    """Attach the requested PicoAOD table sequence to `process`."""
    if enabled_tables is None:
        enabled_tables = ["event", "muons", "electrons", "jets", "met", "custom_objects"]

    table_map = {
        "event": picoEventTables,
        "muons": picoMuonTables,
        "electrons": picoElectronTables,
        "jets": picoJetTables,
        "met": picoMetTables,
        "custom_objects": picoCustomObjectTables,
    }

    unknown = [name for name in enabled_tables if name not in table_map]
    if unknown:
        raise RuntimeError("Unknown PicoAOD table names: %s" % ", ".join(unknown))

    sequence = cms.Sequence()
    for name in enabled_tables:
        sequence += table_map[name]

    process.picoSequence = sequence
    return process.picoSequence


def picoOutputCommands(extra_keep=None):
    commands = cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_*Table_*_*",
        "keep nanoaodUniqueString_nanoMetadata_*_*",
    )
    if extra_keep:
        commands.extend(extra_keep)
    return commands
