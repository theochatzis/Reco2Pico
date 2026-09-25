# Pileup Tools

Tools for pileup handling from Reco2Pico samples.

## Reco2Pico MC bookkeeping

Reco2Pico stores MC normalization and pileup bookkeeping in the `Runs` TTree using a `nanoaod::MergeableCounterTable`.

This keeps the bookkeeping inside the same Pico ROOT file and allows the information to be merged naturally across files and runs.

## Runs format

For MC, the relevant branches are:

```text
Runs
├── run
├── genEventCount
├── genEventSumw
├── genEventSumw2
├── npileupSumw
└── pileupSumw[npileupSumw]
```

### `genEventCount`

Number of generator events processed by Reco2Pico before any Pico skim.

### `genEventSumw`

Sum of generator event weights:

```text
genEventSumw = Σ genWeight
```

This is the quantity used for MC cross-section normalization:

```text
event normalization = cross section × luminosity / genEventSumw
```

### `genEventSumw2`

Sum of squared generator weights:

```text
genEventSumw2 = Σ genWeight²
```

Useful for bookkeeping and effective-statistics calculations.

### `pileupSumw`

Generator-weighted true-pileup distribution.

Conceptually this corresponds to:

```python
pileup.Fill(Pileup_nTrueInt, genWeight)
```

but the histogram bin contents are stored directly as a mergeable vector.

For the default binning:

```text
edges = [0, 1, 2, ..., 100]
```

the vector layout is:

```text
pileupSumw[0]   = underflow
pileupSumw[1]   = 0 <= Pileup_nTrueInt < 1
...
pileupSumw[100] = 99 <= Pileup_nTrueInt < 100
pileupSumw[101] = overflow
```

Therefore:

```text
npileupSumw = 102
```

`npileupSumw` is only the number of stored vector elements; it is not a pileup physics quantity.

If all generator weights are `1`, `pileupSumw` is numerically just the event-count distribution versus `Pileup_nTrueInt`.

For samples with non-unit or negative generator weights, each bin contains the corresponding sum of generator weights.

## Bookkeeping metadata

The bin contents are additive and belong in `Runs`, while the binning itself must not be added when files are merged.

Reco2Pico therefore stores the histogram definition separately in the top-level metadata object:

```text
bookkeepingSchema
```

This is a JSON string stored as a ROOT `TObjString`.

For pileup it contains information such as:

```json
{
  "histograms": {
    "pileup": {
      "contents": "pileupSumw",
      "edges": [0.0, 1.0, 2.0, 3.0],
      "flow_bins": true,
      "variable": "Pileup_nTrueInt",
      "weight": "genWeight",
      "mantissa_bits": 10
    }
  }
}
```

The full edge list is stored in the real file.

This makes the bookkeeping self-describing: downstream code does not need to hardcode the pileup binning.

## Inspecting a Pico file

Open the file with ROOT:

```bash
root -l test_pico.root
```

Inspect the `Runs` tree:

```cpp
Runs->Print();
```

For example:

```cpp
Runs->Scan(
    "run:genEventCount:genEventSumw:genEventSumw2:npileupSumw"
);
```

Inspect the bookkeeping metadata:

```cpp
_file0->ls();

auto *schema =
    (TObjString*)_file0->Get("bookkeepingSchema");

std::cout
    << schema->GetString()
    << std::endl;
```

## Building a pileup histogram from many Pico files

Use:

```text
make_pileup_from_runs.py
```

The script:

- expands the input ROOT files,
- checks that all files use the same pileup bookkeeping schema,
- builds a `TChain("Runs")`,
- sums `pileupSumw` over all `Runs` entries,
- reconstructs a `TH1D`,
- writes it with the name `pileup`,
- copies `bookkeepingSchema` to the output ROOT file.

### Single file

```bash
python3 make_pileup_from_runs.py \
    test_pico.root \
    -o pileup.root
```

### Shell wildcard

```bash
python3 make_pileup_from_runs.py \
    'picos/*.root' \
    -o pileup.root
```

### Recursive wildcard

```bash
python3 make_pileup_from_runs.py \
    'picos/**/*.root' \
    -o pileup.root
```

### Multiple input patterns

```bash
python3 make_pileup_from_runs.py \
    'sample_part1/*.root' \
    'sample_part2/*.root' \
    -o pileup.root
```

### Regular-expression matching

Use `--regex` together with `--search-dir`:

```bash
python3 make_pileup_from_runs.py \
    'pico_.*\.root$' \
    --regex \
    --search-dir /path/to/picos \
    -o pileup.root
```

For example, select only files containing `TTbar`:

```bash
python3 make_pileup_from_runs.py \
    '.*TTbar.*\.root$' \
    --regex \
    --search-dir /path/to/picos \
    -o pileup_TTbar.root
```

## Output

The produced file contains:

```text
pileup.root
├── pileup
└── bookkeepingSchema
```

The script also prints consistency information such as:

```text
pileup integral incl. flow : ...
sum Runs.genEventSumw       : ...
difference                  : ...
sum Runs.genEventCount      : ...
```

For a sample where every processed event has valid pileup information, the pileup integral including underflow and overflow should agree with `genEventSumw`.


