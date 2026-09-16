#ifndef PFRHOSTRIP_RDF_HELPERS_H
#define PFRHOSTRIP_RDF_HELPERS_H

// Helper functions for make_pf_rho_strip_plots_rdf.py.
//
// The functions are intentionally templated/inline so ROOT's Cling can
// instantiate them for std::vector<T>, ROOT::VecOps::RVec<T>, and the
// concrete branch types found in Nano/Pico trees. Keep this header visible
// to the interpreter even when also loading the compiled shared library.

#include <ROOT/RVec.hxx>
#include <algorithm>
#include <cmath>
#include <initializer_list>
#include <map>
#include <set>
#include <utility>
#include <vector>

namespace pf_rdf {
using ROOT::VecOps::RVec;

struct SumCount {
  double sum = 0.0;
  long long n = 0;
};

inline RVec<double> empty_double_vec() { return RVec<double>(); }
inline RVec<int> empty_int_vec() { return RVec<int>(); }

// Unique signed etaBin keys, sorted numerically.
template <class EtaBinVec>
RVec<int> eta_keys(const EtaBinVec &etaBin) {
  std::set<int> keys;
  for (std::size_t i = 0; i < etaBin.size(); ++i) keys.insert(static_cast<int>(etaBin[i]));
  RVec<int> out;
  out.reserve(keys.size());
  for (int k : keys) out.emplace_back(k);
  return out;
}

// Unique |etaBin| keys, sorted numerically.
template <class EtaBinVec>
RVec<int> abs_eta_keys(const EtaBinVec &etaBin) {
  std::set<int> keys;
  for (std::size_t i = 0; i < etaBin.size(); ++i) keys.insert(std::abs(static_cast<int>(etaBin[i])));
  RVec<int> out;
  out.reserve(keys.size());
  for (int k : keys) out.emplace_back(k);
  return out;
}

// Mean eta center per signed etaBin key. The order matches eta_keys().
template <class EtaBinVec, class EtaVec>
RVec<double> eta_centers_by_key(const EtaBinVec &etaBin, const EtaVec &eta) {
  std::map<int, SumCount> acc;
  const std::size_t n = std::min(etaBin.size(), eta.size());
  for (std::size_t i = 0; i < n; ++i) {
    auto &a = acc[static_cast<int>(etaBin[i])];
    a.sum += static_cast<double>(eta[i]);
    a.n += 1;
  }
  RVec<double> out;
  out.reserve(acc.size());
  for (auto const &kv : acc) out.emplace_back(kv.second.n ? kv.second.sum / kv.second.n : 0.0);
  return out;
}

// Mean |eta| center per |etaBin| key. First averages duplicate phi rows per
// signed etaBin, then averages the +eta/-eta sides once per side.
template <class EtaBinVec, class EtaVec>
RVec<double> abs_eta_centers_by_key(const EtaBinVec &etaBin, const EtaVec &eta) {
  std::map<int, SumCount> signed_acc;
  const std::size_t n = std::min(etaBin.size(), eta.size());
  for (std::size_t i = 0; i < n; ++i) {
    auto &a = signed_acc[static_cast<int>(etaBin[i])];
    a.sum += std::abs(static_cast<double>(eta[i]));
    a.n += 1;
  }
  std::map<int, SumCount> abs_acc;
  for (auto const &kv : signed_acc) {
    const int abs_key = std::abs(kv.first);
    auto &a = abs_acc[abs_key];
    a.sum += kv.second.n ? kv.second.sum / kv.second.n : 0.0;
    a.n += 1;
  }
  RVec<double> out;
  out.reserve(abs_acc.size());
  for (auto const &kv : abs_acc) out.emplace_back(kv.second.n ? kv.second.sum / kv.second.n : 0.0);
  return out;
}

// For quantities such as rho: average duplicate phi strip rows in each etaBin.
template <class EtaBinVec, class ValVec>
RVec<double> eta_mean_by_key(const EtaBinVec &etaBin, const ValVec &val) {
  std::map<int, SumCount> acc;
  const std::size_t n = std::min(etaBin.size(), val.size());
  for (std::size_t i = 0; i < n; ++i) {
    auto &a = acc[static_cast<int>(etaBin[i])];
    a.sum += static_cast<double>(val[i]);
    a.n += 1;
  }
  RVec<double> out;
  out.reserve(acc.size());
  for (auto const &kv : acc) out.emplace_back(kv.second.n ? kv.second.sum / kv.second.n : 0.0);
  return out;
}

// For quantities such as n and sumPt: sum phi strip rows in each etaBin.
template <class EtaBinVec, class ValVec>
RVec<double> eta_sum_by_key(const EtaBinVec &etaBin, const ValVec &val) {
  std::map<int, double> acc;
  const std::size_t n = std::min(etaBin.size(), val.size());
  for (std::size_t i = 0; i < n; ++i) acc[static_cast<int>(etaBin[i])] += static_cast<double>(val[i]);
  RVec<double> out;
  out.reserve(acc.size());
  for (auto const &kv : acc) out.emplace_back(kv.second);
  return out;
}

// Occupancy fraction: occupied phi-strip fraction in each etaBin for one event.
template <class EtaBinVec, class NVec>
RVec<double> eta_occupancy_by_key(const EtaBinVec &etaBin, const NVec &nvals) {
  std::map<int, std::pair<long long, long long>> acc;
  const std::size_t n = std::min(etaBin.size(), nvals.size());
  for (std::size_t i = 0; i < n; ++i) {
    auto &a = acc[static_cast<int>(etaBin[i])];
    a.first += (static_cast<double>(nvals[i]) > 0.0) ? 1 : 0;
    a.second += 1;
  }
  RVec<double> out;
  out.reserve(acc.size());
  for (auto const &kv : acc) out.emplace_back(kv.second.second ? double(kv.second.first) / double(kv.second.second) : 0.0);
  return out;
}

// rho contribution in each etaBin:
//   rhoAll(eta) * sumPtFlavor(eta) / sumPtAll(eta)
// with rhoAll averaged over phi rows and sumPt values summed over phi rows.
template <class EtaBinVec, class RhoAllVec, class SumPtAllVec, class SumPtFlavorVec>
RVec<double> eta_contrib_by_key(const EtaBinVec &etaBin,
                                const RhoAllVec &rhoAll,
                                const SumPtAllVec &sumPtAll,
                                const SumPtFlavorVec &sumPtFlavor) {
  std::map<int, SumCount> rho_acc;
  std::map<int, double> sum_all;
  std::map<int, double> sum_flav;
  const std::size_t n = std::min({etaBin.size(), rhoAll.size(), sumPtAll.size(), sumPtFlavor.size()});
  for (std::size_t i = 0; i < n; ++i) {
    const int key = static_cast<int>(etaBin[i]);
    auto &r = rho_acc[key];
    r.sum += static_cast<double>(rhoAll[i]);
    r.n += 1;
    sum_all[key] += static_cast<double>(sumPtAll[i]);
    sum_flav[key] += static_cast<double>(sumPtFlavor[i]);
  }
  RVec<double> out;
  out.reserve(rho_acc.size());
  for (auto const &kv : rho_acc) {
    const int key = kv.first;
    const double rho = kv.second.n ? kv.second.sum / kv.second.n : 0.0;
    const double denom = sum_all[key];
    out.emplace_back(denom > 0.0 ? rho * sum_flav[key] / denom : 0.0);
  }
  return out;
}

// |etaBin| rho used for rho-vs-nPV plots. This first reduces duplicate phi
// rows to one signed-eta value, then averages +eta and -eta values once each.
template <class EtaBinVec, class ValVec>
RVec<double> abs_eta_mean_by_key(const EtaBinVec &etaBin, const ValVec &val) {
  std::map<int, SumCount> signed_acc;
  const std::size_t n = std::min(etaBin.size(), val.size());
  for (std::size_t i = 0; i < n; ++i) {
    auto &a = signed_acc[static_cast<int>(etaBin[i])];
    a.sum += static_cast<double>(val[i]);
    a.n += 1;
  }
  std::map<int, SumCount> abs_acc;
  for (auto const &kv : signed_acc) {
    const int abs_key = std::abs(kv.first);
    auto &a = abs_acc[abs_key];
    a.sum += kv.second.n ? kv.second.sum / kv.second.n : 0.0;
    a.n += 1;
  }
  RVec<double> out;
  out.reserve(abs_acc.size());
  for (auto const &kv : abs_acc) out.emplace_back(kv.second.n ? kv.second.sum / kv.second.n : 0.0);
  return out;
}

// |etaBin| rho contribution used for contribution stacks vs nPV. This computes
// signed-eta contributions first, then averages +eta and -eta once each.
template <class EtaBinVec, class RhoAllVec, class SumPtAllVec, class SumPtFlavorVec>
RVec<double> abs_eta_contrib_by_key(const EtaBinVec &etaBin,
                                    const RhoAllVec &rhoAll,
                                    const SumPtAllVec &sumPtAll,
                                    const SumPtFlavorVec &sumPtFlavor) {
  std::map<int, SumCount> rho_acc;
  std::map<int, double> sum_all;
  std::map<int, double> sum_flav;
  const std::size_t n = std::min({etaBin.size(), rhoAll.size(), sumPtAll.size(), sumPtFlavor.size()});
  for (std::size_t i = 0; i < n; ++i) {
    const int key = static_cast<int>(etaBin[i]);
    auto &r = rho_acc[key];
    r.sum += static_cast<double>(rhoAll[i]);
    r.n += 1;
    sum_all[key] += static_cast<double>(sumPtAll[i]);
    sum_flav[key] += static_cast<double>(sumPtFlavor[i]);
  }

  std::map<int, SumCount> abs_acc;
  for (auto const &kv : rho_acc) {
    const int key = kv.first;
    const double rho = kv.second.n ? kv.second.sum / kv.second.n : 0.0;
    const double denom = sum_all[key];
    const double contrib = denom > 0.0 ? rho * sum_flav[key] / denom : 0.0;
    auto &a = abs_acc[std::abs(key)];
    a.sum += contrib;
    a.n += 1;
  }

  RVec<double> out;
  out.reserve(abs_acc.size());
  for (auto const &kv : abs_acc) out.emplace_back(kv.second.n ? kv.second.sum / kv.second.n : 0.0);
  return out;
}

// Select entries whose integer key matches target.
template <class KeyVec, class ValVec>
RVec<double> select_by_key(const KeyVec &keys, const ValVec &vals, int target) {
  RVec<double> out;
  const std::size_t n = std::min(keys.size(), vals.size());
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    if (static_cast<int>(keys[i]) == target) out.emplace_back(static_cast<double>(vals[i]));
  }
  return out;
}

// Replicate a scalar to match the length of a vector column.
template <class Vec>
RVec<double> fill_like(const Vec &v, double value) {
  RVec<double> out(v.size());
  for (std::size_t i = 0; i < v.size(); ++i) out[i] = value;
  return out;
}

// Phi plot x-values for a selected etaBin.
template <class EtaBinVec, class PhiVec>
RVec<double> phi_x_for_eta(const EtaBinVec &etaBin, const PhiVec &phi, int targetEtaBin) {
  RVec<double> out;
  const std::size_t n = std::min(etaBin.size(), phi.size());
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    if (static_cast<int>(etaBin[i]) == targetEtaBin) out.emplace_back(static_cast<double>(phi[i]));
  }
  return out;
}

// Phi plot raw row values for a selected etaBin.
template <class EtaBinVec, class ValVec>
RVec<double> rows_for_eta(const EtaBinVec &etaBin, const ValVec &val, int targetEtaBin) {
  RVec<double> out;
  const std::size_t n = std::min(etaBin.size(), val.size());
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    if (static_cast<int>(etaBin[i]) == targetEtaBin) out.emplace_back(static_cast<double>(val[i]));
  }
  return out;
}

// Phi plot occupancy for a selected etaBin: one row per phi strip.
template <class EtaBinVec, class NVec>
RVec<double> occupancy_rows_for_eta(const EtaBinVec &etaBin, const NVec &nvals, int targetEtaBin) {
  RVec<double> out;
  const std::size_t n = std::min(etaBin.size(), nvals.size());
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    if (static_cast<int>(etaBin[i]) == targetEtaBin) out.emplace_back(static_cast<double>(nvals[i]) > 0.0 ? 1.0 : 0.0);
  }
  return out;
}

// Phi plot rho contribution per phi strip.
template <class EtaBinVec, class RhoAllVec, class SumPtAllVec, class SumPtFlavorVec>
RVec<double> contrib_rows_for_eta(const EtaBinVec &etaBin,
                                  const RhoAllVec &rhoAll,
                                  const SumPtAllVec &sumPtAll,
                                  const SumPtFlavorVec &sumPtFlavor,
                                  int targetEtaBin) {
  RVec<double> out;
  const std::size_t n = std::min({etaBin.size(), rhoAll.size(), sumPtAll.size(), sumPtFlavor.size()});
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    if (static_cast<int>(etaBin[i]) != targetEtaBin) continue;
    const double denom = static_cast<double>(sumPtAll[i]);
    const double val = denom > 0.0 ? static_cast<double>(rhoAll[i]) * static_cast<double>(sumPtFlavor[i]) / denom : 0.0;
    out.emplace_back(val);
  }
  return out;
}

} // namespace pf_rdf

namespace pf_rdf {
int library_marker();
}

#endif  // PFRHOSTRIP_RDF_HELPERS_H
