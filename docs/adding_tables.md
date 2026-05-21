# Adding new PicoAOD tables

1. Add a new file under `python/tables/`, for example `genparticles_cff.py`.
2. Define one or more `FlatTableProducer` modules.
3. Wrap them in a `cms.Sequence`.
4. Import the sequence in `python/pico_cff.py`.
5. Add the table group name to `table_map`.
6. Run with `tables=...` in `cmsRun`.
