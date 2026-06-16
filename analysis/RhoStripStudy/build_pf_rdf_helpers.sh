#!/usr/bin/env bash
set -euo pipefail

# Build the optional helper shared library for make_pf_rho_strip_plots_rdf.py.
# Requires ROOT to be available in the environment and root-config on PATH.

cxx=${CXX:-c++}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

"${cxx}" -O3 -DNDEBUG -std=c++17 -fPIC -shared \
  "${script_dir}/PFRhoStripRDFHelpers.cc" \
  -o "${script_dir}/libPFRhoStripRDFHelpers.so" \
  $(root-config --cflags --libs)

echo "Built ${script_dir}/libPFRhoStripRDFHelpers.so"
