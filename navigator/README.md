# NavigatorTool

Shows where each module takes its inputs from, and where every piece is
defined, so that new code can be read by following the dataflow instead of
searching for it. It works on three kinds of input, each giving one
self-contained HTML page (no network needed) or a text tree in the terminal:

| Mode | Input | Answers |
|---|---|---|
| config | a `cmsRun` configuration | which module feeds which, and the python and C++ lines behind each |
| `--pico FILE` | a Pico file (and, for old files, the configuration that made it) | the above, plus where each branch of the file is defined |
| `--edm FILE` | an EDM file (RAW, RECO, AOD, MiniAOD) | which module of which process made each product, and what it actually read |

## Configurations

The configuration is loaded the way `cmsRun` loads it (eras, modifiers,
customisations and command-line options all applied). For each module the page
shows:

- the python line that created it (`cms.EDProducer(...)` or `.clone(...)`), the
  chain of clones back to the original, and any later line that changed an
  InputTag (a `toModify`, a customisation function, `process.x.src = ...`);
- the C++ behind its type: the class or typedef, the template if it is one, the
  `DEFINE_FWK_MODULE` line, the `produces<...>` lines, and the lines that read
  each input parameter (constructor and `fillDescriptions`);
- each InputTag it consumes and the module that produces it, or "from input
  file" when no module of this process does.

```bash
NAV=$CMSSW_BASE/src/Reco2Pico/navigator/navigator.py
cd $CMSSW_BASE/src/Reco2Pico/PicoProducer/python/workflows

python3 $NAV -o reco_nav.html RECO_to_pico_cfg.py \
    isMC=true inputFiles=file:dummy.root tables=event,muons,jets,genparts,sim,pfcands,recojets

# upstream tree in the terminal
python3 $NAV --tree picoPFJetGenMatchTable --depth 2 RECO_to_pico_cfg.py isMC=true inputFiles=file:dummy.root ...
```

Tool options go before the configuration; everything after it is passed to
the configuration, as with `cmsRun`. The input file is not opened, but
configurations that check their arguments still need one.

One page per Pico tier (MiniAOD, AOD, RECO), with every table group the tier
supports switched on (MC):

```bash
$CMSSW_BASE/src/Reco2Pico/navigator/make_all_pico_navigators.sh   # writes navigator/out/
```

Modules in no path or task are hidden by default (`unscheduled` shows them
faded). They never run, so an InputTag pointing to one is a parameter that the
C++ does not use in this setup.

## Pico files

A Pico file is a flat NanoAOD-format tree: branches such as `Jet_pt`, grouped
into tables (`Jet`) with a row count (`nJet`). Picos made since
`PicoMetadataProducer` (October 2026) describe themselves, so the file is
enough:

```bash
python3 $NAV -o pico_nav.html --pico pico.root
```

The file holds two strings, written by the `nanoMetadata` module of the Pico
job (`PicoProducer/python/tables/metadata_cff.py`):

- `picoCommand`: the configuration, a SHA-1 of its contents, the arguments and
  the release. The navigator loads the configuration at the recorded path
  under `$CMSSW_BASE/src`, or any `*_cfg.py` there with the same contents (the
  batch chains run renamed copies such as `cfgs/ntuple_reco-pico_cfg.py`), with
  the recorded arguments. It warns if the configuration changed since, or if the
  release differs.
- `picoProvenance`: the module writing each table (and its extensions), and
  for every module behind the tables the products it actually read, taken from
  the framework's parentage during the job.

Each branch is then traced to

- its table and the module writing it, as recorded;
- the line defining the column: the `Var(...)`/`ExtVar(...)` in python (followed
  through clones and shared blocks such as `P4Vars` in NanoAOD's `common_cff.py`),
  or the `addColumn<...>("col", ...)` in C++ on that table's object. A name
  the C++ builds, such as `addColumn("puInteraction" + n)` or an array of
  names (`ootBxm5`, ...), points to that line. `run`, `luminosityBlock` and
  `event` point to the output module, which writes them.

The recorded reads are compared with the InputTags of the configuration. An
InputTag the module never read is marked *not read in the job*: on the test
Pico this flags 19 parameters of the PAT producers whose features are switched
off (e.g. `picoPatMuons.pfMuonSource`). A product read without any InputTag
naming it becomes an input too. When a string parameter of the module holds
its label, the input is named after it, with the C++ lines reading it, e.g.
`picoSimCaloTable` reads 20 products of `picoSimCaloCandidates` through
`src (string)`; otherwise it is "(found at run time)", e.g. `allConversions`,
which `PATElectronProducer` hard-codes.

The page gets a *Branches* tab: pick a table to see its branches with type,
documentation string and definition line, while the graph shows the module
writing it. On a 5-event Pico of the `run3_mix` chain (every table group and
the pile-up truth), all 671 branches in 62 tables are traced, in about 15 s.

Older Picos record neither string. Give the configuration with the arguments
of the job that made the file; the writer of each table is then guessed from
names (a configuration string equal to the table name, a name written in the
C++, or one built from the configuration such as `name_ + "GenMatch"`):

```bash
python3 $NAV -o pico_nav.html --pico pico.root RECO_to_pico_cfg.py isMC=true inputFiles=file:dummy.root tables=...
```

A configuration given after `--pico` is always used (with a warning when it is
not the recorded one); arguments given after it replace the recorded ones.

Besides these strings, `NanoAODOutputModule` writes the `MetaData` tree (the
process history, e.g. SIM → HLT → RECO → PICO with their releases) and the
`ParameterSets` tree (the parameters of every module of every process).
`edmProvDump` reads both.

## EDM files

An EDM file carries its own provenance, the same information `edmProvDump`
prints:

- the process history, with the release of each process;
- for every product: C++ type, module label, instance and process, e.g.
  `recoTracks_generalTracks__RECO`;
- for the module that made it: its C++ type and complete parameters;
- its parentage: the products that module actually read while running,
  recorded per event. This is more reliable than InputTags in a configuration,
  because parameters the C++ does not use never appear.

Ancestors of kept products keep their provenance even when the products
themselves were dropped, so the chain stays complete. `--edm` turns this into a
page:

```bash
python3 $NAV -o reco_file.html --edm step1.root          # also root://... with a grid proxy
python3 $NAV --tree generalTracks:RECO --depth 2 --edm step1.root
```

- Modules are grouped by process (newest first) and named `label:PROCESS`.
- Each module lists its products and whether each was kept in the file or
  dropped. A module whose products were all dropped has a dashed outline.
- Edges are the products read, labelled with the parameter that names them
  where a matching InputTag exists, otherwise "(found at run time)".
- Associators and value maps (e.g. track ↔ TrackingParticle, PFCandidate value
  maps) are ordinary modules here: their inputs show exactly which collections
  they link.
- The C++ is looked up in the current release. A module that ran in another
  release (e.g. SIM and HLT in `CMSSW_15_0_18`) is marked, since lines can differ.
- The page starts one step upstream: a full reconstruction fans out quickly.

On the local RECOSIM test file (SIM, HLT, RECO) this gives 763 modules and
about 2000 edges, in about a minute (`edmProvDump` takes a third of it).

## The page

- Left: modules grouped by origin (your C++ plugin, your configuration with a
  CMSSW plugin, CMSSW, input file) or, for EDM files, by process. Search
  matches labels and C++ types.
- Centre: the selected module with its upstream and downstream neighbours.
  Click a box for details, double-click to recentre, `←` to go back. Hovering
  a box highlights its edges and names the parameters they come through.
- Right: code snippets around every reference with the line highlighted.
  `copy` puts `absolute/path:line` on the clipboard; release files also get an
  `open` link to GitHub at the release tag.

Open a module directly with `page.html#LABEL`, or pass `--focus LABEL`. For
links to your own files, pass a template with `{path}` and `{line}`, e.g.
`--link 'vscode://vscode-remote/ssh-remote+lxplus.cern.ch{path}:{line}'`.

## Limits

- Configurations: only InputTag edges are followed. Products selected by
  `outputCommands`, `ESInputTag`s and labels passed as plain strings are not.
- C++ lines are found by matching quoted names in the plugin's files, so a
  parameter or column name built at run time from other strings is not found.
- Pico: the recorded reads are those of the events of the job's first run,
  so an input read only in rare events may be missing; tables first written
  after the first run are not listed. Old Picos assume the configuration given
  matches the job that made the file.
- EDM: parentage is read from the stored provenance; EventSetup modules are
  left out.
- Pages are snapshots. Rerun after changing code, configuration or file.

The first run in a release spends about 30 s indexing the C++ plugins of the
release; the index is cached in `~/.cache/navigator/`. Pages are 0.3–1.5 MB
for configurations and Pico files, and about 5 MB for a full RECO file. Most of
it is embedded code snippets and stored parameters.

The tool is `navigator.py` plus `navigator_template.html`; copy both to use it
elsewhere. It needs only the python of a CMSSW release. The template has no
data and is not meant to be opened; open the generated file. Pages written to
`out/` are ignored by git.
