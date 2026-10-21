#!/usr/bin/env python3
"""NavigatorTool: map the module dataflow of a cmsRun configuration or file.

Three modes, each writing one self-contained HTML file (no network needed)
with an interactive upstream/downstream graph:

  config  Loads the configuration exactly as cmsRun would (modifiers,
          customisations and command-line options applied) and records for
          every module where it is defined in python (creation or .clone line,
          clone chain, later modifications), the C++ behind it (class, template,
          DEFINE_FWK_MODULE, produces<...>, the lines reading each input), and
          which module produces each InputTag it consumes.
  --pico  The same, plus every branch of a Pico (NanoAOD-format) file traced
          to its table, the module writing it, and the python Var(...) or C++
          addColumn line that defines the column. Picos made with
          PicoMetadataProducer record their configuration and arguments
          (picoCommand) and which module wrote each table and what it read
          (picoProvenance): the configuration is then optional, and the
          writers and inputs are the recorded ones.
  --edm   Reads the provenance stored in an EDM file (RAW, RECO, AOD, MiniAOD):
          every module of every process that made a product in the file, its
          parameters, the products it actually read (recorded parentage), and
          which products were kept in the file or dropped.

Usage (inside cmsenv):
  navigator.py [-o page.html] [--focus LABEL] CFG.py [cfg args ...]
  navigator.py [-o page.html] --pico PICO.root [CFG.py [cfg args ...]]
  navigator.py [-o page.html] --edm FILE.root
  navigator.py --tree LABEL [--depth N] (CFG.py [cfg args ...] | --edm FILE.root)

Options for the tool go before the configuration file; everything after the
configuration file is passed to it, as with cmsRun.
"""

import argparse
import copy
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

SELF = os.path.realpath(__file__)
FWCORE_PS = os.sep + os.path.join("FWCore", "ParameterSet") + os.sep
# python helpers whose own lines are never the interesting definition site
HELPER_FILES = (os.path.join("PhysicsTools", "NanoAOD", "python", "common_cff.py"),)
GITHUB = "https://github.com/cms-sw/cmssw/blob"
CXX_EXT = (".cc", ".cpp", ".cxx", ".cu", ".h", ".hpp", ".hh")
DEFINE_RE = re.compile(r"DEFINE_FWK_(?:ALPAKA_)?MODULE\s*\(\s*([A-Za-z_][\w:]*)\s*\)")
TABLE_LITERAL_RE = re.compile(r'FlatTable>\s*\([^;]*?"(\w+)"')
ADD_COLUMN_RE = re.compile(r'addColumn(?:Value)?\s*<[^>]+>\s*\(\s*"(\w+)"')
BRANCH_RE = re.compile(r'\bBranch\s*\(\s*"(\w+)"')  # branches the output module writes itself
COLUMN_ON_RE = re.compile(r'(\w+)\s*(?:->|\.)\s*addColumn(?:Value)?\s*<[^>]+>\s*\(\s*"(\w+)"')
TABLE_VAR_RE = re.compile(r'(\w+)\s*=\s*std::make_unique<\s*nanoaod::FlatTable\s*>\s*\(([^;]*)\)\s*;')
QUOTED_RE = re.compile(r'"(\w+)"')
STRING_MEMBER_RE = re.compile(r'(\w+)\s*\(\s*\w+\s*\.\s*get(?:Untracked)?Parameter<\s*std::string\s*>\s*\(\s*"(\w+)"\s*\)\s*\)')


# ---------------------------------------------------------------------------
# Python side: record where configuration objects are created and modified
# ---------------------------------------------------------------------------

class SiteRecorder:
    """Hooks into FWCore.ParameterSet to remember file:line of each object."""

    def __init__(self):
        self.created = {}      # id(obj) -> (obj, site)
        self.cloned_from = {}  # id(obj) -> source obj
        self.assigned = {}     # (id(obj), name) -> (obj, site)
        self._real = {}

    def _realpath(self, fn):
        if fn not in self._real:
            self._real[fn] = os.path.realpath(fn)
        return self._real[fn]

    def site(self):
        """First stack frame outside FWCore/ParameterSet, helpers and this tool."""
        f = sys._getframe(1)
        while f is not None:
            fn = f.f_code.co_filename
            if not fn.startswith("<") and FWCORE_PS not in fn:
                real = self._realpath(fn)
                helper = f.f_code.co_name != "<module>" and real.endswith(HELPER_FILES)
                if real != SELF and FWCORE_PS not in real and not helper:
                    return (real, f.f_lineno)
            f = f.f_back
        return None

    def install(self):
        from FWCore.ParameterSet.Mixins import _Parameterizable, _TypedParameterizable

        rec = self
        orig_init = _Parameterizable.__init__
        orig_clone = _TypedParameterizable.clone
        orig_setattr = _Parameterizable.__setattr__

        def init(obj, *args, **kwargs):
            if id(obj) not in rec.created:
                rec.created[id(obj)] = (obj, rec.site())
            orig_init(obj, *args, **kwargs)

        def clone(obj, *args, **kwargs):
            new = orig_clone(obj, *args, **kwargs)
            rec.created[id(new)] = (new, rec.site())
            rec.cloned_from[id(new)] = obj
            return new

        def setattr_(obj, name, value):
            orig_setattr(obj, name, value)
            if not name.startswith("_"):
                rec.assigned[(id(obj), name)] = (obj, rec.site())

        def deepcopy_(obj, memo):
            # clone() and PSet(block, ...) deep-copy parameters; keep their sites
            new = copy._reconstruct(obj, memo, *obj.__reduce_ex__(4))
            site = rec.created_site(obj)
            if site:
                rec.created[id(new)] = (new, site)
            return new

        _Parameterizable.__init__ = init
        _TypedParameterizable.clone = clone
        _Parameterizable.__setattr__ = setattr_
        _Parameterizable.__deepcopy__ = deepcopy_

    def created_site(self, obj):
        entry = self.created.get(id(obj))
        return entry[1] if entry and entry[0] is obj else None

    def assigned_site(self, obj, name):
        entry = self.assigned.get((id(obj), name))
        return entry[1] if entry and entry[0] is obj else None


# ---------------------------------------------------------------------------
# Source references and snippets
# ---------------------------------------------------------------------------

class Sources:
    """Turns (file, line) into display paths, links and embedded snippets."""

    def __init__(self, link_template=None):
        self.base = os.path.realpath(os.environ["CMSSW_BASE"]) if os.environ.get("CMSSW_BASE") else None
        self.release = os.path.realpath(os.environ["CMSSW_RELEASE_BASE"]) if os.environ.get("CMSSW_RELEASE_BASE") else None
        self.version = os.environ.get("CMSSW_VERSION", "")
        self.link_template = link_template
        self.snippets = {}
        self._lines = {}

    def lines(self, path):
        if path not in self._lines:
            try:
                with open(path, errors="replace") as f:
                    self._lines[path] = f.read().splitlines()
            except OSError:
                self._lines[path] = []
        return self._lines[path]

    def origin(self, path):
        if self.base and path.startswith(self.base + os.sep):
            return "generated" if "/cfipython/" in path else "local"
        if self.release and path.startswith(self.release + os.sep):
            return "generated" if "/cfipython/" in path else "release"
        return "other"

    def display(self, path):
        for root, tag in ((self.base, "$CMSSW_BASE"), (self.release, "$CMSSW_RELEASE_BASE")):
            if root and path.startswith(root + os.sep):
                rel = path[len(root) + 1:]
                return rel[4:] if rel.startswith("src/") else tag + "/" + rel
        return path

    def url(self, path, line):
        if self.release and path.startswith(self.release + "/src/") and self.version:
            return "%s/%s/%s#L%d" % (GITHUB, self.version, path[len(self.release) + 5:], line)
        if self.link_template:
            return self.link_template.format(path=path, line=line)
        return None

    def ref(self, path, line, context=5):
        """Register a snippet and return its key (None if unreadable)."""
        if not path or not line:
            return None
        key = "%s:%d" % (path, line)
        if key in self.snippets:
            return key
        lines = self.lines(path)
        if not lines:
            return None
        start = max(1, line - context)
        stop = min(len(lines), line + context)
        self.snippets[key] = {
            "path": self.display(path),
            "abs": path,
            "line": line,
            "start": start,
            "code": lines[start - 1:stop],
            "url": self.url(path, line),
            "origin": self.origin(path),
        }
        return key


# ---------------------------------------------------------------------------
# C++ side: find the plugin behind each module type
# ---------------------------------------------------------------------------

def grep_defines(root):
    """Map plugin name -> (file, line) for DEFINE_FWK_MODULE under root."""
    found = {}
    if not root or not os.path.isdir(root):
        return found
    cmd = ["grep", "-rIn", "-E", r"DEFINE_FWK_(ALPAKA_)?MODULE"]
    cmd += ["--include=*%s" % e for e in CXX_EXT]
    cmd += ["--exclude-dir=.git", "--exclude-dir=__pycache__", root]
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout
    for row in out.splitlines():
        try:
            path, line, text = row.split(":", 2)
        except ValueError:
            continue
        if text.lstrip().startswith(("//", "#define")):
            continue
        for name in DEFINE_RE.findall(text):
            found.setdefault(name.split("::")[-1], (path, int(line)))
    return found


def release_index(release, version):
    cache_dir = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "navigator")
    cache = os.path.join(cache_dir, "%s_%s.json" % (version, os.environ.get("SCRAM_ARCH", "arch")))
    try:
        with open(cache) as f:
            return {k: tuple(v) for k, v in json.load(f).items()}
    except (OSError, ValueError):
        pass
    print("navigator: indexing C++ plugins of %s (once, cached in %s)" % (version, cache), file=sys.stderr)
    index = grep_defines(os.path.join(release, "src"))
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache, "w") as f:
            json.dump(index, f)
    except OSError:
        pass
    return index


class CppIndex:
    def __init__(self, sources):
        self.src = sources
        self.local = grep_defines(os.path.join(sources.base, "src")) if sources.base else {}
        self.release = release_index(sources.release, sources.version) if sources.release else {}
        self._pkg_files = {}
        self._described = {}

    def find(self, type_name):
        name = type_name.split("@")[0].split("::")[-1]
        return self.local.get(name) or self.release.get(name)

    def package_files(self, path):
        """All C++ files of the Subsystem/Package that contains path."""
        parts = path.split(os.sep)
        try:
            i = len(parts) - 1 - parts[::-1].index("src")
        except ValueError:
            return [path]
        pkg = os.sep.join(parts[:i + 3])
        if pkg not in self._pkg_files:
            files = []
            for d in ("plugins", "interface", "src"):
                for root, _, names in os.walk(os.path.join(pkg, d)):
                    files += [os.path.join(root, n) for n in sorted(names) if n.endswith(CXX_EXT)]
            self._pkg_files[pkg] = files
        return self._pkg_files[pkg]

    def search(self, files, pattern, limit):
        hits = []
        for path in files:
            for n, text in enumerate(self.src.lines(path), 1):
                if pattern.search(text) and not text.lstrip().startswith(("//", "/*", "*")):
                    hits.append((path, n))
                    if len(hits) >= limit:
                        return hits
        return hits

    def describe(self, type_name, params):
        key = (type_name, tuple(params))
        if key not in self._described:
            self._described[key] = self._describe(type_name, params)
        return self._described[key]

    def _describe(self, type_name, params):
        hit = self.find(type_name)
        if not hit:
            return None
        define_file, define_line = hit
        name = type_name.split("@")[0].split("::")[-1]
        files = self.package_files(define_file)
        ordered = [define_file] + [f for f in files if f != define_file]
        info = {"define": self.src.ref(define_file, define_line, 3),
                "origin": self.src.origin(define_file), "cls": None,
                "produces": [], "params": {}}

        # class, struct, typedef or using declaration of the plugin name
        decl = re.compile(r"(\b(class|struct)\s+%s\b(?!\s*;)|\btypedef\b.*\b%s\s*;|\busing\s+%s\s*=)" % ((re.escape(name),) * 3))
        cls = self.search(ordered, decl, 1)
        cls_file = define_file
        if cls:
            cls_file = cls[0][0]
            info["cls"] = self.src.ref(*cls[0], context=4)
            text = self.src.lines(cls[0][0])[cls[0][1] - 1]
            alias = re.search(r"(?:typedef|=)\s*([A-Za-z_][\w:]*)\s*<", text)
            if alias:  # a template instantiation: show the template too
                template = alias.group(1).split("::")[-1]
                tmpl = self.search(ordered, re.compile(r"\b(class|struct)\s+%s\b(?!\s*;)" % re.escape(template)), 1)
                if tmpl:
                    cls_file = tmpl[0][0]
                    info["template"] = self.src.ref(*tmpl[0], context=4)

        first = [define_file] if cls_file == define_file else [cls_file, define_file]
        rest = [f for f in ordered if f not in first]
        info["produces"] = [self.src.ref(p, n, 2) for p, n in
                            self.search(first, re.compile(r"\bproduces\s*<"), 8)]
        reader = re.compile(r"getParameter|getUntrackedParameter|consumes|InputTag|\badd(Untracked|Optional)?\s*<")
        for param in params:
            quoted = re.compile(r'"%s"' % re.escape(param))
            hits = [h for h in self.search(first, quoted, 12) if reader.search(self.src.lines(h[0])[h[1] - 1])]
            if not hits:
                hits = [h for h in self.search(rest, quoted, 12) if reader.search(self.src.lines(h[0])[h[1] - 1])]
            info["params"][param] = [self.src.ref(p, n, 3) for p, n in hits[:3]]

        # FlatTable names written literally and columns added in C++ (Pico mode),
        # in the plugin's own files and the local headers they include
        near = first + [f for f in self.includes(first) if f not in first]
        tables, columns, occurrences, table_vars, members, quoted = set(), {}, [], {}, {}, {}
        for path in near:
            text = "\n".join(self.src.lines(path))
            line = lambda pos: text.count("\n", 0, pos) + 1
            tables.update(TABLE_LITERAL_RE.findall(text))
            for regex in (ADD_COLUMN_RE, BRANCH_RE):
                for m in regex.finditer(text):
                    columns.setdefault(m.group(1), (path, line(m.start(1))))
            # which table object each column goes to, and how that table is named
            for m in COLUMN_ON_RE.finditer(text):
                occurrences.append((m.group(2), m.group(1), path, line(m.start(2))))
            for m in TABLE_VAR_RE.finditer(text):
                args = m.group(2).split(",")
                if len(args) > 1:
                    table_vars[m.group(1)] = args[1].strip()
            members.update({k: v for k, v in STRING_MEMBER_RE.findall(text)})
            for m in QUOTED_RE.finditer(text):
                quoted.setdefault(m.group(1), (path, line(m.start(1))))
        info.update(_tables=tables, _columns=columns, _occurrences=occurrences,
                    _table_vars=table_vars, _members=members, _quoted=quoted)
        return info

    def includes(self, files):
        """Headers included with quotes that exist next to the file or in a src area."""
        found = []
        roots = [os.path.join(r, "src") for r in (self.src.base, self.src.release) if r]
        for path in files:
            for text in self.src.lines(path):
                m = re.match(r'\s*#\s*include\s+"([^"]+)"', text)
                if not m:
                    continue
                for cand in [os.path.join(os.path.dirname(path), m.group(1))] + [os.path.join(r, m.group(1)) for r in roots]:
                    if os.path.isfile(cand):
                        found.append(os.path.realpath(cand))
                        break
        return found


def public(info):
    """C++ info without the private fields used only during extraction."""
    return {k: v for k, v in info.items() if not k.startswith("_")} if info else None


# ---------------------------------------------------------------------------
# Config mode
# ---------------------------------------------------------------------------

def walk_tags(cms, pset, path, rec, out):
    """Collect (param path, InputTag, modification site) inside a PSet."""
    for name in pset.parameterNames_():
        value = getattr(pset, name)
        here = path + [name]
        site = rec.assigned_site(pset, name)
        if isinstance(value, cms.InputTag):
            out.append((".".join(here), name, value, site))
        elif isinstance(value, cms.VInputTag):
            for i, tag in enumerate(value):
                tag = tag if isinstance(tag, cms.InputTag) else cms.InputTag(str(tag))
                out.append(("%s[%d]" % (".".join(here), i), name, tag, site))
        elif isinstance(value, cms.PSet):
            walk_tags(cms, value, here, rec, out)
        elif isinstance(value, cms.VPSet):
            for i, sub in enumerate(value):
                walk_tags(cms, sub, path + ["%s[%d]" % (name, i)], rec, out)


def scheduled_labels(process):
    labels = set()
    groups = [process.paths_(), process.endpaths_()]
    if hasattr(process, "finalpaths_"):
        groups.append(process.finalpaths_())
    for group in groups:
        for seq in group.values():
            try:
                labels.update(seq.moduleNames())
            except Exception:
                pass
    if process.schedule_() is not None:
        try:
            labels.update(process.schedule_().moduleNames())
        except Exception:
            pass
        for task in getattr(process.schedule_(), "_tasks", []):
            try:
                labels.update(task.moduleNames())
            except Exception:
                pass
    return labels


def process_modules(process):
    modules = []
    for kind, getter in (("producer", "producers_"), ("filter", "filters_"),
                         ("analyzer", "analyzers_"), ("output", "outputModules_"),
                         ("switch", "switchProducers_")):
        if hasattr(process, getter):
            modules += [(kind, label, mod) for label, mod in getattr(process, getter)().items()]
    return modules


CONFIG_GROUPS = [["local", "Your C++ plugins"], ["localcfg", "Your config, CMSSW plugins"],
                 ["release", "CMSSW modules"], ["input", "From the input file"]]


def build(process, rec, src, cpp):
    import FWCore.ParameterSet.Config as cms

    current = process.name_()
    scheduled = scheduled_labels(process)
    modules = process_modules(process)
    aliases = process.aliases_() if hasattr(process, "aliases_") else {}
    known = {label for _, label, _ in modules} | set(aliases)

    nodes, edges = {}, {}

    def py_info(obj):
        site = rec.created_site(obj)
        chain, seen, parent = [], set(), rec.cloned_from.get(id(obj))
        while parent is not None and id(parent) not in seen and len(chain) < 8:
            seen.add(id(parent))
            label = parent.label_() if parent.hasLabel_() else None
            psite = rec.created_site(parent)
            chain.append({"label": label, "type": parent.type_(),
                          "ref": src.ref(*psite) if psite else None})
            parent = rec.cloned_from.get(id(parent))
        return {"ref": src.ref(*site) if site else None,
                "origin": src.origin(site[0]) if site else "other",
                "clonedFrom": chain}

    def add_edge(producer, consumer, param, tag, set_ref):
        e = edges.setdefault((producer, consumer), {"from": producer, "to": consumer, "params": []})
        e["params"].append({"param": param, "tag": tag, "set": set_ref})

    def resolve(tag):
        label = tag.getModuleLabel()
        proc = tag.getProcessName()
        if proc in ("", current, "@currentProcess") and label in known:
            return label
        node_id = "input:" + label + (":" + proc if proc else "")
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "kind": "input", "group": "input",
                              "type": "from input file" + (" (process %s)" % proc if proc else ""),
                              "origin": "input", "scheduled": True, "inputs": []}
        return node_id

    for kind, label, mod in modules:
        cases = [(None, mod)]
        if kind == "switch":
            cases = [(c, getattr(mod, c)) for c in mod.parameterNames_()]
        types, inputs = [], []
        for case, obj in cases:
            if not hasattr(obj, "type_"):
                continue
            types.append(obj.type_() if case is None else "%s: %s" % (case, obj.type_()))
            found = []
            walk_tags(cms, obj, [case] if case else [], rec, found)
            inputs += [(case, obj, f) for f in found]
        base = cases[0][1]
        param_names = sorted({f[1] for _, _, f in inputs})
        cxx = cpp.describe(base.type_(), param_names) if hasattr(base, "type_") else None
        node = {"id": label, "label": label, "kind": kind, "type": " | ".join(types),
                "scheduled": label in scheduled or kind == "output", "py": py_info(base),
                "cpp": public(cxx), "inputs": []}
        node["origin"] = "local" if (cxx and cxx["origin"] == "local") else (
            "localcfg" if node["py"]["origin"] == "local" else "release")
        node["group"] = node["origin"]
        try:
            dump = base.dumpPython()
        except Exception:
            dump = ""
        node["dump"] = dump if len(dump) < 6000 else dump[:6000] + "\n... (truncated)"
        for case, obj, (path, name, tag, site) in inputs:
            if not tag.getModuleLabel():
                continue
            producer = resolve(tag)
            created = rec.created_site(obj)
            set_ref = src.ref(*site) if site and site != created else None
            text = tag.encode() if hasattr(tag, "encode") else tag.value()
            node["inputs"].append({"param": path, "name": name, "tag": text,
                                   "from": producer, "set": set_ref})
            add_edge(producer, label, path, text, set_ref)
        nodes[label] = node

    for label, alias in aliases.items():
        node = {"id": label, "label": label, "kind": "alias", "type": "EDAlias", "group": "release",
                "scheduled": True, "origin": "release", "inputs": [], "cpp": None,
                "py": py_info(alias), "dump": alias.dumpPython()}
        for target in alias.parameterNames_():
            producer = resolve(cms.InputTag(target))
            node["inputs"].append({"param": target, "name": target, "tag": target,
                                   "from": producer, "set": None})
            add_edge(producer, label, target, target, None)
        nodes[label] = node

    return {"nodes": nodes, "edges": list(edges.values()), "snippets": src.snippets,
            "groups": CONFIG_GROUPS}


# ---------------------------------------------------------------------------
# Pico mode: trace each branch of a NanoAOD-format file to its definition
# ---------------------------------------------------------------------------

def read_branches(path):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kError
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        sys.exit("navigator: cannot open %s" % path)
    tree = f.Get("Events")
    if not tree:
        sys.exit("navigator: %s has no Events tree; is it a Pico/NanoAOD file?" % path)
    out = []
    for br in tree.GetListOfBranches():
        leaf = br.GetListOfLeaves()[0]
        out.append({"name": br.GetName(), "ctype": leaf.GetTypeName(), "doc": br.GetTitle()})
    entries = tree.GetEntries()
    f.Close()
    return out, entries


def read_pico_strings(path):
    """The nanoMetadata strings of a Pico file, e.g. picoProvenance and picoCommand."""
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kError
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        sys.exit("navigator: cannot open %s" % path)
    out = {}
    for key in f.GetListOfKeys():
        if key.GetClassName() == "TObjString":
            out[key.GetName()] = str(key.ReadObj().GetString())
    f.Close()
    for name in ("picoProvenance", "picoCommand"):
        if name in out:
            try:
                out[name] = json.loads(out[name])
            except ValueError:
                print("navigator: %s of %s is not valid JSON, ignored" % (name, path), file=sys.stderr)
                del out[name]
    return out


def file_sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def find_config(command):
    """The configuration a Pico job ran, from its picoCommand string.

    The recorded path is tried first, relative to $CMSSW_BASE/src. Jobs often
    run a renamed copy, so otherwise every *_cfg.py under $CMSSW_BASE/src with
    the same contents is a match. Returns (path, changed) or (None, None)."""
    src = os.path.join(os.environ["CMSSW_BASE"], "src")
    recorded = command["config"] if os.path.isabs(command["config"]) else os.path.join(src, command["config"])
    if os.path.isfile(recorded) and file_sha1(recorded) == command["sha1"]:
        return recorded, False
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "plots", "output")]
        for name in files:
            if name.endswith("_cfg.py") and file_sha1(os.path.join(root, name)) == command["sha1"]:
                return os.path.join(root, name), False
    if os.path.isfile(recorded):
        return recorded, True
    return None, None


def string_values(cms, pset, out):
    for name in pset.parameterNames_():
        value = getattr(pset, name)
        if isinstance(value, cms.string):
            out.add(value.value())
        elif isinstance(value, cms.PSet):
            string_values(cms, value, out)
        elif isinstance(value, cms.VPSet):
            for sub in value:
                string_values(cms, sub, out)


def config_columns(cms, mod, rec, src):
    """Columns declared in the configuration: variables / externalVariables."""
    cols = {}
    for block, kind in (("variables", "Var"), ("externalVariables", "ExtVar")):
        if not hasattr(mod, block) or not isinstance(getattr(mod, block), cms.PSet):
            continue
        pset = getattr(mod, block)
        for col in pset.parameterNames_():
            spec = getattr(pset, col)
            site = rec.assigned_site(pset, col) or rec.created_site(spec)
            how = ""
            if isinstance(spec, cms.PSet):
                if hasattr(spec, "expr"):
                    how = "%s(%r)" % (kind, spec.expr.value())
                elif hasattr(spec, "src"):
                    how = "%s(%s)" % (kind, spec.src.value())
            cols[col] = {"ref": src.ref(*site, context=3) if site else None, "how": how}
    return cols


def resolve_table_name(cms, expr, members, mod):
    """Evaluate a C++ table-name expression such as name_ + "GenMatch"."""
    out = ""
    for term in expr.split("+"):
        term = term.strip()
        literal = re.fullmatch(r'(?:std::string\s*\(\s*)?"(\w*)"\s*\)?', term)
        if literal:
            out += literal.group(1)
            continue
        param = members.get(term)
        value = getattr(mod, param, None) if param and hasattr(mod, param) else None
        if not isinstance(value, cms.string):
            return None
        out += value.value()
    return out


def built_column(col, writers):
    """A column whose name the C++ builds at run time: addColumn("prefix" + n)
    with a numeric suffix, or a name spelled out elsewhere in the plugin (e.g. an
    array of names). Returns (writer, (path, line)) or None."""
    for w in writers:
        stem = col.rstrip("0123456789")
        if stem != col and stem in w["cpp"]:
            return w, w["cpp"][stem]
    for w in writers:
        if col in w["quoted"]:
            return w, w["quoted"][col]
    return None


def build_pico(data, process, rec, src, cpp, path, prov=None):
    """prov: the file's picoProvenance, if stored. It names the module writing
    each table exactly; without it the writer is guessed from table names."""
    import FWCore.ParameterSet.Config as cms

    branches, entries = read_branches(path)
    names = {b["name"] for b in branches}

    # what each module can write: table names and columns
    writers = []
    for kind, label, mod in process_modules(process):
        if kind == "switch" or label not in data["nodes"]:
            continue
        strings = set()
        string_values(cms, mod, strings)
        cxx = cpp.describe(mod.type_(), []) if hasattr(mod, "type_") else None
        literals = cxx["_tables"] if cxx else set()
        cpp_cols = cxx["_columns"] if cxx else {}
        cfg_cols = config_columns(cms, mod, rec, src)
        if not (cfg_cols or cpp_cols or literals):
            continue
        # table name of each C++ table object, e.g. name_ + "GenMatch" with name_ from the config
        table_names, table_cols = {}, {}
        if cxx:
            for var, expr in cxx["_table_vars"].items():
                table_names[var] = resolve_table_name(cms, expr, cxx["_members"], mod)
            for col, var, cpath, cline in cxx["_occurrences"]:
                if table_names.get(var) is not None:
                    table_cols.setdefault((table_names[var], col), (cpath, cline))
        writers.append({"label": label, "strings": strings, "literals": literals,
                        "names": {n for n in table_names.values() if n}, "table_cols": table_cols,
                        "cfg": cfg_cols, "cpp": cpp_cols, "quoted": cxx["_quoted"] if cxx else {},
                        "output": kind == "output"})
    outputs = [w for w in writers if w["output"]]
    writers = [w for w in writers if not w["output"]]

    def table_of(branch):
        if "_" in branch:
            return branch.split("_", 1)
        if branch[:1] == "n" and any(n.startswith(branch[1:] + "_") for n in names):
            return branch[1:], None  # the row count of a table
        return "", branch

    tables = {}
    for b in branches:
        key, col = table_of(b["name"])
        t = tables.setdefault(key, {"name": key or "(event level)", "columns": [], "modules": []})
        if col is None:
            t["counter"] = b["name"]
            continue
        t["columns"].append(dict(b, column=col, module=None, ref=None, how=""))

    recorded = prov["tables"] if prov else {}
    for key, t in tables.items():
        cols = {c["column"] for c in t["columns"]}
        if key in recorded:
            # main table first, then its extensions
            labels = [w["module"] for w in sorted(recorded[key], key=lambda w: w["extension"])]
            strong = sorted((w for w in writers if w["label"] in labels), key=lambda w: labels.index(w["label"]))
            weak = outputs
            missing = [l for l in labels if l not in data["nodes"]]
            if missing:
                print("navigator: table %s was written by %s, not in this configuration"
                      % (key, ", ".join(missing)), file=sys.stderr)
            t["recorded"] = True
        else:
            # an empty table name (event-level singletons) matches too many strings
            strong = [w for w in writers if key and (key in w["names"] or key in w["strings"] or key in w["literals"])]
            weak = [w for w in writers if key and w not in strong and cols & set(w["cpp"]) and
                    any(len(s) > 1 and key.startswith(s) for s in w["strings"] | w["literals"])]
            weak += outputs
        candidates = strong if key in recorded else writers
        used = []
        for c in t["columns"]:
            col = c["column"]
            for w in strong:
                if col in w["cfg"]:
                    c.update(module=w["label"], ref=w["cfg"][col]["ref"], how=w["cfg"][col]["how"])
                    break
            else:
                exact = [w for w in candidates if (key, col) in w["table_cols"]]
                if exact:
                    w = exact[0]
                    c.update(module=w["label"], ref=src.ref(*w["table_cols"][(key, col)], context=3), how="addColumn")
                    if w["label"] not in used:
                        used.append(w["label"])
                    continue
                for w in strong + weak:
                    if col in w["cpp"]:
                        c.update(module=w["label"], ref=src.ref(*w["cpp"][col], context=3), how="addColumn")
                        break
                else:
                    built = built_column(col, strong)
                    if built:
                        w, site = built
                        c.update(module=w["label"], ref=src.ref(*site, context=3), how="addColumn")
                    elif len(strong) == 1:
                        c["module"] = strong[0]["label"]
            if c["module"] and c["module"] not in used:
                used.append(c["module"])
        if key in recorded:
            t["modules"] = [w["label"] for w in strong]
        else:
            t["modules"] = used or [w["label"] for w in strong]
        for label in t["modules"]:
            data["nodes"][label].setdefault("tables", []).append(key)

    data["tables"] = sorted(tables.values(), key=lambda t: t["name"].lower())
    data["pico"] = {"file": path, "entries": entries, "branches": len(branches), "provenance": bool(prov)}
    if prov:
        labels = {label: string_params(cms, mod) for _, label, mod in process_modules(process)}
        apply_reads(data, prov, labels, cpp)


def string_params(cms, pset, prefix=""):
    """{value: [parameter names]} of the string parameters of a module."""
    out = {}
    for name in pset.parameterNames_():
        value = getattr(pset, name)
        if isinstance(value, cms.string) and value.value():
            out.setdefault(value.value(), []).append(prefix + name)
        elif isinstance(value, cms.PSet):
            for v, names in string_params(cms, value, prefix + name + ".").items():
                out.setdefault(v, []).extend(names)
    return out


def apply_reads(data, prov, labels, cpp):
    """Compare the InputTags of the configuration with what each module read in
    the job (picoProvenance "modules"): mark InputTags never read, and add the
    reads no InputTag names: products whose label comes from a string parameter
    (labels: {module: {value: [parameter names]}}), is hard-coded, or is found
    by type (e.g. GetterOfProducts)."""
    nodes, process = data["nodes"], prov["process"]
    edges = {(e["from"], e["to"]): e for e in data["edges"]}

    def source(label, proc):
        if proc == process and label in nodes:
            return label
        for node_id in ("input:%s:%s" % (label, proc), "input:" + label):
            if node_id in nodes:
                return node_id
        node_id = "input:%s:%s" % (label, proc)
        nodes[node_id] = {"id": node_id, "label": label, "kind": "input", "group": "input",
                          "type": "from input file (process %s)" % proc,
                          "origin": "input", "scheduled": True, "inputs": []}
        return node_id

    for label, reads in prov["modules"].items():
        node = nodes.get(label)
        if not node:
            continue
        node["recorded"] = True
        found = {}
        for product in reads:
            _, plabel, _, proc = split_branch(product)
            found.setdefault(source(plabel, proc), []).append(product)
        for inp in node["inputs"]:
            inp["read"] = inp["from"] in found
        covered = {inp["from"] for inp in node["inputs"]}
        for src_id, products in sorted(found.items()):
            if src_id in covered:
                continue
            plabel = nodes[src_id]["label"]
            via = labels.get(label, {}).get(plabel)
            param = ", ".join(via) + " (string)" if via else "(found at run time)"
            if via and node.get("cpp") and via[0] not in node["cpp"]["params"]:
                cxx = cpp.describe(node["type"], [via[0]])
                node["cpp"]["params"][via[0]] = cxx["params"][via[0]] if cxx else []
            for product in products:
                node["inputs"].append({"param": param, "name": via[0] if via else "", "tag": product,
                                       "from": src_id, "set": None, "read": True})
                e = edges.get((src_id, label))
                if not e:
                    e = edges[(src_id, label)] = {"from": src_id, "to": label, "params": []}
                    data["edges"].append(e)
                e["params"].append({"param": param, "tag": product, "set": None})


# ---------------------------------------------------------------------------
# EDM mode: provenance stored in the file
# ---------------------------------------------------------------------------

def split_branch(branch):
    """'recoTracks_generalTracks__RECO.' -> (type, label, instance, process)."""
    parts = branch.rstrip(".").split("_")
    if len(parts) < 4:
        return (branch, "", "", "")
    return ("_".join(parts[:-3]), parts[-3], parts[-2], parts[-1])


def parse_provenance(text):
    """Parse 'edmProvDump -e -d' output."""
    history, modules = [], []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"\s+(\w+) '\"?([\w.-]+)\"?' \[\d+\]", line)
        if m and not modules:
            history.append((m.group(1), m.group(2)))
        m = re.match(r"Module: (\S+) (\S+)", line)
        if m:
            mod = {"label": m.group(1), "process": m.group(2), "products": [],
                   "params": [], "deps": [], "type": "", "edm": ""}
            block = None
            i += 1
            while i < len(lines) and not lines[i].startswith("Module: ") and not lines[i].startswith("---"):
                l = lines[i]
                head = re.match(r" (products|parameters|dependencies): \{", l)
                if head:
                    block = head.group(1)
                elif l.startswith(" }"):
                    block = None
                elif block == "products":
                    mod["products"].append(l.strip().split()[0])
                elif block == "dependencies":
                    mod["deps"].append(l.strip())
                elif block == "parameters":
                    mod["params"].append(l[2:])
                    t = re.match(r"\s*@module_type: string tracked\s+= '(.*)'", l)
                    if t:
                        mod["type"] = t.group(1)
                    t = re.match(r"\s*@module_edm_type: string tracked\s+= '(.*)'", l)
                    if t:
                        mod["edm"] = t.group(1)
                i += 1
            modules.append(mod)
            continue
        i += 1
    return history, modules


def kept_products(path):
    out = subprocess.run(["edmDumpEventContent", path], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True).stdout
    kept = set()
    for row in out.splitlines():
        q = re.findall(r'"([^"]*)"', row)
        if len(q) == 3:
            kept.add(tuple(q))
    return kept


def build_edm(path, src, cpp):
    print("navigator: reading provenance of %s" % path, file=sys.stderr)
    dump = subprocess.run(["edmProvDump", "-e", "-d", path], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    if dump.returncode != 0:
        sys.exit("navigator: edmProvDump failed:\n" + dump.stderr[-2000:])
    history, modules = parse_provenance(dump.stdout)
    kept = kept_products(path)
    releases = dict(history)
    order = {p: i for i, (p, _) in enumerate(history)}

    producer_of, nodes, edges = {}, {}, {}
    for mod in modules:
        mid = "%s:%s" % (mod["label"], mod["process"])
        for p in mod["products"]:
            producer_of[p.rstrip(".")] = mid

    for mod in modules:
        mid = "%s:%s" % (mod["label"], mod["process"])
        # InputTag parameters, to name the parameter behind each dependency
        tags = []
        for l in mod["params"]:
            m = re.match(r"\s*(\w+): (V?InputTag) \w+\s+= \{?([^}]*)\}?", l)
            if m:
                for v in m.group(3).split(","):
                    if v.strip():
                        tags.append((m.group(1), v.strip().split(":")))
        products = []
        for p in mod["products"]:
            t, label, inst, proc = split_branch(p)
            products.append({"name": p.rstrip("."), "type": t, "instance": inst,
                             "kept": (label, inst, proc) in kept})
        inputs = []
        for d in mod["deps"]:
            t, label, inst, proc = split_branch(d)
            params = [n for n, v in tags if v[0] == label and (v[1] if len(v) > 1 else "") == inst
                      and (len(v) < 3 or v[2] in ("", proc))]
            src_id = producer_of.get(d.rstrip("."))
            if not src_id:
                src_id = "unknown:%s:%s" % (label, proc)
                nodes.setdefault(src_id, {"id": src_id, "label": label, "kind": "input", "group": proc,
                                          "type": "provenance not stored", "origin": "input",
                                          "scheduled": True, "inputs": []})
            inputs.append({"param": ", ".join(sorted(set(params))) or "(found at run time)",
                           "name": params[0] if params else "", "tag": d.rstrip("."),
                           "from": src_id, "set": None})
            e = edges.setdefault((src_id, mid), {"from": src_id, "to": mid, "params": []})
            e["params"].append({"param": inputs[-1]["param"], "tag": d.rstrip("."), "set": None})
        cxx = cpp.describe(mod["type"], sorted({n for n, _ in tags})) if mod["type"] else None
        text = "\n".join(mod["params"])
        nodes[mid] = {
            "id": mid, "label": mod["label"], "kind": (mod["edm"] or "module").lower(),
            "type": mod["type"] or mod["edm"], "process": mod["process"],
            "release": releases.get(mod["process"], ""), "group": mod["process"],
            "origin": "local" if cxx and cxx["origin"] == "local" else "release",
            "scheduled": True, "dropped": bool(products) and not any(p["kept"] for p in products),
            "py": None, "cpp": public(cxx), "inputs": inputs, "products": products,
            "dump": text if len(text) < 8000 else text[:8000] + "\n... (truncated)",
        }

    groups = [[p, "%s  (%s)" % (p, r)] for p, r in sorted(history, key=lambda h: -order[h[0]])]
    return {"nodes": nodes, "edges": list(edges.values()), "snippets": src.snippets,
            "groups": groups, "history": history}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def loc(data, key):
    if not key:
        return "?"
    s = data["snippets"][key]
    return "%s:%d" % (s["path"], s["line"])


def print_tree(data, label, depth):
    nodes = data["nodes"]
    if label not in nodes:
        close = [n for n in nodes if label.lower() in n.lower()][:10]
        sys.exit("navigator: no module '%s'. Close matches: %s" % (label, ", ".join(close) or "none"))

    def describe(node):
        text = "%s  [%s]" % (node["id"], node["type"])
        if not node["scheduled"]:
            text += "  (in no path or task: never runs)"
        if node.get("dropped"):
            text += "  (products dropped from the file)"
        if node.get("py") and node["py"]["ref"]:
            text += "\n    py : %s" % loc(data, node["py"]["ref"])
        if node.get("cpp") and (node["cpp"].get("cls") or node["cpp"].get("define")):
            text += "\n    c++: %s" % loc(data, node["cpp"].get("cls") or node["cpp"]["define"])
        return text

    seen = set()

    def visit(node_id, prefix, level, via):
        node = nodes[node_id]
        lines = describe(node).split("\n")
        print(prefix + (via + " <- " if via else "") + lines[0])
        for extra in lines[1:]:
            print(prefix + "   " + extra.strip())
        if node_id in seen:
            if node["inputs"]:
                print(prefix + "   (inputs shown above)")
            return
        seen.add(node_id)
        if level >= depth:
            if node["inputs"]:
                print(prefix + "   ... %d more inputs (raise --depth)" % len(node["inputs"]))
            return
        for inp in node["inputs"]:
            visit(inp["from"], prefix + "   ", level + 1, "%s=%s" % (inp["param"], inp["tag"]))

    visit(label, "", 0, None)


def write_html(data, path):
    template_path = os.path.join(os.path.dirname(SELF), "navigator_template.html")
    with open(template_path) as f:
        page = f.read()
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("/*__NAVIGATOR_DATA__*/null", blob)
    with open(path, "w") as f:
        f.write(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", nargs="?", help="cmsRun python configuration")
    parser.add_argument("config_args", nargs=argparse.REMAINDER, help="arguments passed to the configuration")
    parser.add_argument("-o", "--output", default=None, help="HTML file to write (default: <input>_navigator.html)")
    parser.add_argument("--focus", default=None, help="module shown first when the page opens")
    parser.add_argument("--pico", metavar="FILE", help="also trace the branches of this Pico (NanoAOD-format) file")
    parser.add_argument("--edm", metavar="FILE", help="read the provenance of this EDM file instead of a configuration")
    parser.add_argument("--tree", metavar="LABEL", help="print the upstream tree of LABEL instead of writing HTML")
    parser.add_argument("--depth", type=int, default=3, help="depth of --tree (default 3)")
    parser.add_argument("--link", default=None,
                        help="link template for files outside the release, e.g. 'vscode://file{path}:{line}'")
    opts = parser.parse_args()

    if "CMSSW_BASE" not in os.environ:
        sys.exit("navigator: run inside a CMSSW environment (cmsenv)")
    if bool(opts.edm) == bool(opts.config or opts.pico):
        parser.error("give a configuration, --pico FILE, or --edm FILE")

    strings = read_pico_strings(opts.pico) if opts.pico else {}
    command = strings.get("picoCommand")
    if command:
        if command.get("release") and command["release"] != os.environ.get("CMSSW_VERSION"):
            print("navigator: the Pico was made in %s, this is %s" % (command["release"], os.environ.get("CMSSW_VERSION")),
                  file=sys.stderr)
        if not opts.config:
            opts.config, changed = find_config(command)
            if not opts.config:
                sys.exit("navigator: the Pico was made by %s, which is not in $CMSSW_BASE/src; "
                         "give the configuration after --pico FILE" % command["config"])
            if changed:
                print("navigator: %s changed since the Pico was made" % opts.config, file=sys.stderr)
            print("navigator: configuration from the file: %s" % opts.config, file=sys.stderr)
        elif file_sha1(opts.config) != command["sha1"]:
            print("navigator: %s is not the configuration the Pico was made with (%s)" % (opts.config, command["config"]),
                  file=sys.stderr)
        if not opts.config_args:
            opts.config_args = command["args"]
    elif opts.pico and not opts.config:
        parser.error("%s does not record its configuration (made before picoCommand); give it after --pico FILE"
                     % opts.pico)

    src = Sources(opts.link)
    if opts.edm:
        data = build_edm(opts.edm, src, CppIndex(src))
        meta = {"mode": "edm", "config": opts.edm, "args": [],
                "process": " → ".join(p for p, _ in data["history"])}
        stem = opts.edm
    else:
        rec = SiteRecorder()
        rec.install()
        from FWCore.ParameterSet.processFromFile import processFromFile
        sys.path.append(os.getcwd())
        config = os.path.realpath(opts.config)
        process = processFromFile(config, opts.config_args)
        cpp = CppIndex(src)
        data = build(process, rec, src, cpp)
        meta = {"mode": "config", "config": src.display(config), "args": opts.config_args,
                "process": process.name_()}
        stem = config
        if opts.pico:
            build_pico(data, process, rec, src, cpp, opts.pico, strings.get("picoProvenance"))
            meta["mode"] = "pico"
            stem = opts.pico
    meta.update(release=src.version, focus=opts.focus,
                generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    data["meta"] = meta

    if opts.tree:
        print_tree(data, opts.tree, opts.depth)
        return
    if opts.focus and opts.focus not in data["nodes"]:
        close = [n for n in data["nodes"] if opts.focus.lower() in n.lower()][:10]
        sys.exit("navigator: no module '%s'. Close matches: %s" % (opts.focus, ", ".join(close) or "none"))
    out = opts.output or os.path.splitext(os.path.basename(stem))[0] + "_navigator.html"
    write_html(data, out)
    n_mod = sum(1 for n in data["nodes"].values() if n["kind"] != "input")
    summary = "%d modules, %d external inputs, %d edges" % (n_mod, len(data["nodes"]) - n_mod, len(data["edges"]))
    if "tables" in data:
        traced = sum(1 for t in data["tables"] for c in t["columns"] if c["ref"])
        total = sum(len(t["columns"]) for t in data["tables"])
        summary += ", %d tables, %d/%d branches traced to a line" % (len(data["tables"]), traced, total)
    print("navigator: %s -> %s" % (summary, out))


if __name__ == "__main__":
    main()
