#!/usr/bin/env python3
"""
make_ntuple_doc.py -- variable documentation (HTML + CSV) for a NanoAOD-style ntuple.

    python3 make_ntuple_doc.py FILE.root [-o doc.html] [--csv vars.csv] [--title T] [--max-events N]

Same spirit as PicoProducer/python/workflows/make_workbook.py (one DataTable per
collection, size pie chart) with, in addition, the fill statistics that tell
whether a table or a branch actually carries information:

  * per collection: mean multiplicity, fraction of events with >= 1 entry, size;
    collections that are empty in every event are flagged EMPTY
  * per branch: number of distinct values, min / max (numeric), fraction of
    entries equal to the most common value -> constant placeholders such as
    -999 or -1 stand out

The description column is the NanoAOD `doc` string stored as the branch title.
"""
import argparse
import json
import os
import sys
from html import escape

import numpy as np
import uproot


def analyse(fname, max_events):
    f = uproot.open(fname)
    tree = f['Events']
    n_events = tree.num_entries
    n_read = n_events if max_events <= 0 else min(n_events, max_events)
    names = tree.keys()
    counters = {n[1:] for n in names if n.startswith('n') and any(m.startswith(n[1:] + '_') for m in names)}
    arrays = tree.arrays(names, entry_stop=n_read, library='np')

    rows, colls = [], {}
    for name in names:
        br = tree[name]
        coll = name.split('_')[0] if '_' in name else ('n' and name[1:] if name.startswith('n') and name[1:] in counters else 'Event')
        if name.startswith('n') and name[1:] in counters:
            coll = name[1:]
        size_kb = br.compressed_bytes / 1024.0 / n_events if n_events else 0.0
        a = arrays[name]
        flat = np.concatenate([np.asarray(x).ravel() for x in a]) if a.dtype == object else np.asarray(a).ravel()
        n_entries = int(flat.size)
        distinct = minv = maxv = const_frac = ''
        if n_entries:
            try:
                u, c = np.unique(flat, return_counts=True)
                distinct = int(u.size)
                const_frac = float(c.max()) / n_entries
                if np.issubdtype(flat.dtype, np.number):
                    minv, maxv = float(np.nanmin(flat)), float(np.nanmax(flat))
            except TypeError:
                pass
        rows.append(dict(collection=coll, variable=name, type=str(br.typename), size_kb_per_event=size_kb,
                         doc=str(br.title or ''), entries=n_entries, distinct=distinct, min=minv, max=maxv,
                         const_frac=const_frac))
        colls.setdefault(coll, dict(size=0.0, mult=None, frac=None))
        colls[coll]['size'] += size_kb
        if name.startswith('n') and name[1:] == coll:
            cnt = np.asarray(a, dtype=float)
            colls[coll]['mult'] = float(cnt.mean()) if cnt.size else 0.0
            colls[coll]['frac'] = float((cnt > 0).mean()) if cnt.size else 0.0
    return n_events, n_read, rows, colls


def fmt(v, nd=4):
    if v == '' or v is None:
        return ''
    if isinstance(v, float):
        return ('{:.' + str(nd) + 'g}').format(v)
    return str(v)


def write_csv(rows, path):
    import csv
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['collection', 'variable', 'type', 'size_kb_per_event', 'doc',
                                           'entries', 'distinct', 'min', 'max', 'const_frac'])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r['collection'], r['variable'])):
            w.writerow(r)


def write_html(path, title, fname, n_events, n_read, rows, colls):
    order = ['Event'] + sorted(c for c in colls if c != 'Event')
    summary = []
    for c in order:
        info = colls[c]
        status = ''
        if info['mult'] is not None:
            status = 'EMPTY' if info['frac'] == 0 else ('sparse' if info['frac'] < 0.5 else '')
        summary.append('<tr class="{cls}"><td><a href="#{a}"><code>{c}</code></a></td><td>{m}</td><td>{f}</td>'
                       '<td>{s:.4f}</td><td>{st}</td></tr>'.format(
                           cls='empty' if status == 'EMPTY' else '', a=escape(c), c=escape(c),
                           m='' if info['mult'] is None else '{:.3g}'.format(info['mult']),
                           f='' if info['frac'] is None else '{:.0%}'.format(info['frac']),
                           s=info['size'], st=status))
    sections = []
    for c in order:
        sub = sorted((r for r in rows if r['collection'] == c), key=lambda r: r['variable'])
        trs = []
        for r in sub:
            cls = ''
            if r['const_frac'] != '' and r['entries'] > 1 and r['const_frac'] >= 0.999:
                cls = 'const'
            trs.append('<tr class="{cls}"><td><code>{v}</code></td><td><code>{t}</code></td><td>{s:.6f}</td>'
                       '<td>{e}</td><td>{d}</td><td>{mn}</td><td>{mx}</td><td>{cf}</td><td>{doc}</td></tr>'.format(
                           cls=cls, v=escape(r['variable']), t=escape(r['type']), s=r['size_kb_per_event'],
                           e=r['entries'], d=fmt(r['distinct']), mn=fmt(r['min']), mx=fmt(r['max']),
                           cf='' if r['const_frac'] == '' else '{:.0%}'.format(r['const_frac']),
                           doc=escape(r['doc'])))
        info = colls[c]
        sections.append('''
<h2 id="{a}">{c}</h2>
<p class="size-summary"><b>Total size:</b> {s:.6f} KB/event{mult}</p>
<table class="display compact cell-border">
<thead><tr><th>Variable</th><th>Type</th><th>Size [KB/event]</th><th>Entries</th><th>Distinct</th>
<th>Min</th><th>Max</th><th>Most common</th><th>Description</th></tr></thead>
<tbody>{rows}</tbody></table>'''.format(
            a=escape(c), c=escape(c), s=info['size'],
            mult='' if info['mult'] is None else ' &nbsp; <b>Mean multiplicity:</b> {:.3g} &nbsp; <b>Events with &ge;1:</b> {:.0%}'.format(info['mult'], info['frac']),
            rows='\n'.join(trs)))
    pie = sorted(((c, colls[c]['size']) for c in colls), key=lambda x: -x[1])
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
<style>
body {{ font-family: Arial, Helvetica, sans-serif; margin: 2rem; max-width: 1700px; }}
h1 {{ margin-bottom: 0.3rem; }}
.subtitle {{ color: #555; margin-bottom: 2rem; }}
h2 {{ margin-top: 3rem; padding-bottom: 0.3rem; border-bottom: 2px solid #cccccc; }}
table {{ width: 100%; margin-top: 1rem; margin-bottom: 2rem; }}
td, th {{ vertical-align: top; padding: 6px; }}
code {{ background: #f3f3f3; padding: 2px 4px; border-radius: 4px; }}
tr.empty td {{ background: #fde8e8; }}
tr.const td {{ background: #fff6dd; }}
.size-summary {{ font-size: 0.95rem; color: #333; margin: 0.8rem 0; }}
.legend {{ font-size: 0.9rem; color: #444; }}
.chart-box {{ width: 100%; max-width: 900px; height: 520px; margin: 1rem 0 3rem 0; }}
</style></head><body>
<h1>{title}</h1>
<p class="subtitle">Automatically generated from the "Events" TTree of <code>{fname}</code>.<br>
Events in file: {n_events}; statistics computed on {n_read} events.</p>
<p class="legend">Rows shaded red: collection empty in every event. Rows shaded yellow: branch with a
single value in all entries (constant or placeholder such as -999 / -1). "Most common" is the fraction of
entries equal to the most frequent value.</p>
<h2 id="summary">Collections</h2>
<table id="summary-table" class="display compact cell-border">
<thead><tr><th>Collection</th><th>Mean multiplicity</th><th>Events with &ge;1</th><th>Size [KB/event]</th><th>Status</th></tr></thead>
<tbody>{summary}</tbody></table>
{sections}
<h2>Size by collection</h2>
<div id="collection-size-pie" class="chart-box"></div>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<script>
$(document).ready(function() {{
  $('table.display').not('#summary-table').DataTable({{ paging: false, searching: true, info: false, order: [[0, 'asc']] }});
  $('#summary-table').DataTable({{ paging: false, searching: true, info: false, order: [[3, 'desc']] }});
  Plotly.newPlot('collection-size-pie', [{{ type: 'pie', labels: {labels}, values: {values},
    textinfo: 'label+percent', hovertemplate: '%{{label}}<br>%{{value:.6f}} KB/event<extra></extra>' }}],
    {{ title: 'Total size by collection [KB/event]', height: 520 }});
}});
</script></body></html>
'''.format(title=escape(title), fname=escape(os.path.basename(fname)), n_events=n_events, n_read=n_read,
           summary='\n'.join(summary), sections=''.join(sections),
           labels=json.dumps([p[0] for p in pie]), values=json.dumps([p[1] for p in pie]))
    with open(path, 'w') as fh:
        fh.write(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file')
    ap.add_argument('-o', '--output', help='HTML output (default: doc_<file>.html next to the input)')
    ap.add_argument('--csv', help='also write the table as CSV')
    ap.add_argument('--title', default=None)
    ap.add_argument('--max-events', type=int, default=2000, help='events used for the statistics (0 = all)')
    args = ap.parse_args()
    out = args.output or os.path.join(os.path.dirname(args.file) or '.',
                                      'doc_' + os.path.splitext(os.path.basename(args.file))[0] + '.html')
    title = args.title or 'Ntuple doc: ' + os.path.basename(args.file)
    n_events, n_read, rows, colls = analyse(args.file, args.max_events)
    write_html(out, title, args.file, n_events, n_read, rows, colls)
    if args.csv:
        write_csv(rows, args.csv)
    empty = sorted(c for c, i in colls.items() if i['frac'] == 0)
    print('[make_ntuple_doc] {}: {} events, {} branches, {} collections -> {}'.format(
        args.file, n_events, len(rows), len(colls), out))
    if empty:
        print('[make_ntuple_doc] collections empty in every event: ' + ' '.join(empty))
    return 0


if __name__ == '__main__':
    sys.exit(main())
