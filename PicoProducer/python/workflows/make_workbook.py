import uproot
import pandas as pd
import json
from html import escape

# =========================================================
# Read ROOT file
# =========================================================

f = uproot.open("test_pico.root")
tree = f["Events"]

n_events = tree.num_entries

# =========================================================
# Extract branches
# =========================================================

rows = []

for name, branch in tree.items():

    if "_" in name:
        collection = name.split("_")[0]
    else:
        collection = "Event"

    size_kb = branch.compressed_bytes / 1024
    size_kb_per_event = size_kb / n_events if n_events > 0 else 0

    rows.append({
        "collection": collection,
        "variable": str(name),
        "type": str(branch.typename),
        "size_kb_per_event": size_kb_per_event,
        "doc": str(branch.title) if branch.title is not None else ""
    })

# =========================================================
# Build dataframe
# =========================================================

df = pd.DataFrame(rows)

for col in ["collection", "variable", "type", "doc"]:
    if col not in df.columns:
        df[col] = ""
    df[col] = df[col].fillna("").astype(str)

df["size_kb_per_event"] = df["size_kb_per_event"].fillna(0.0).astype(float)

df = df.sort_values(["collection", "variable"])

df.to_csv("PicoAOD_variables.csv", index=False)

print("Saved PicoAOD_variables.csv")

# =========================================================
# Pie chart data
# =========================================================

collection_sizes = (
    df.groupby("collection")["size_kb_per_event"]
      .sum()
      .reset_index()
      .sort_values("size_kb_per_event", ascending=False)
)

pie_labels = collection_sizes["collection"].tolist()
pie_values = collection_sizes["size_kb_per_event"].tolist()

# =========================================================
# Build HTML sections
# =========================================================

sections = []

collections = ["Event"] + sorted(c for c in df["collection"].unique() if c != "Event")

for coll in collections:

    sub = df[df["collection"] == coll]
    total_kb_per_event = sub["size_kb_per_event"].sum()

    table_rows = []

    for r in sub.itertuples(index=False):
        table_rows.append(
            f"""
            <tr>
              <td><code>{escape(r.variable)}</code></td>
              <td><code>{escape(r.type)}</code></td>
              <td>{r.size_kb_per_event:.6f}</td>
              <td>{escape(r.doc)}</td>
            </tr>
            """
        )

    rows_html = "\n".join(table_rows)

    sections.append(f"""
    <h2>{escape(coll)}</h2>

    <p class="size-summary">
      <b>Total size:</b> {total_kb_per_event:.6f} KB/event
    </p>

    <table class="display compact cell-border">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Type</th>
          <th>Size [KB/event]</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    """)

# =========================================================
# Full HTML page
# =========================================================

html = f"""
<!doctype html>

<html lang="en">

<head>

<meta charset="utf-8">

<title>PicoAOD Doc</title>

<link rel="stylesheet"
href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 2rem;
    max-width: 1600px;
}}

h1 {{
    margin-bottom: 0.3rem;
}}

.subtitle {{
    color: #555;
    margin-bottom: 2rem;
}}

h2 {{
    margin-top: 3rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #cccccc;
}}

table {{
    width: 100%;
    margin-top: 1rem;
    margin-bottom: 2rem;
}}

td, th {{
    vertical-align: top;
    padding: 6px;
}}

code {{
    background: #f3f3f3;
    padding: 2px 4px;
    border-radius: 4px;
}}

.dataTables_filter {{
    margin-bottom: 1rem;
}}

.size-summary {{
    font-size: 0.95rem;
    color: #333;
    margin-top: 0.8rem;
    margin-bottom: 0.8rem;
}}

.chart-box {{
    width: 100%;
    max-width: 900px;
    height: 520px;
    margin-top: 1rem;
    margin-bottom: 3rem;
}}

</style>

</head>

<body>

<h1>PicoAOD Doc</h1>

<p class="subtitle">
Automatically generated variable documentation from PicoAOD ROOT file "Events" TTree.<br>
Number of events: {n_events}
</p>

{''.join(sections)}

<h2>Size by collection</h2>
<div id="collection-size-pie" class="chart-box"></div>

<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>

<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>

<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>

<script>

$(document).ready(function() {{

    $('table.display').DataTable({{
        paging: false,
        searching: true,
        info: false,
        order: [[2, 'desc']]
    }});

    Plotly.newPlot('collection-size-pie', [{{
        type: 'pie',
        labels: {json.dumps(pie_labels)},
        values: {json.dumps(pie_values)},
        textinfo: 'label+percent',
        hovertemplate: '%{{label}}<br>%{{value:.6f}} KB/event<extra></extra>'
    }}], {{
        title: 'Total size by collection [KB/event]',
        height: 520
    }});

}});

</script>

</body>
</html>
"""

# =========================================================
# Write HTML
# =========================================================

with open("doc_PicoAOD.html", "w") as fout:
    fout.write(html)

print("Saved doc_PicoAOD.html")