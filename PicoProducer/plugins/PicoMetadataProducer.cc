// PicoMetadataProducer: the nanoMetadata module of a Pico job.
//
// NanoAODOutputModule writes every nanoaod::UniqueString made by the module
// labelled "nanoMetadata" as a TObjString in the output file, named by the
// product instance. This module does what UniqueStringProducer does (one
// string per entry of the "strings" PSet) and adds one more, the provenance
// of the Pico tables that NanoAOD files otherwise lack:
//
//   {"version": 1, "process": "PICO",
//    "tables":  {"Jet": [{"module": "picoJetTable", "instance": "", "extension": false}, ...], ...},
//    "modules": {"picoJetTable": ["patJets_picoPatJets__PICO", ...], ...}}
//
// "tables" maps each FlatTable name to the modules writing it (the main table
// and its extensions). "modules" lists, for every module of this process that
// a table depends on, the products it actually read (event parentage), so the
// chain back to the input file is complete. Module types and parameters are
// already in the file's ParameterSets tree.
//
// NanoAODOutputModule refuses a string that changes between runs of one job,
// so the provenance is frozen at the end of the first run: later runs repeat
// it. Tables that first appear after the first run are therefore not listed.

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/NanoAOD/interface/UniqueString.h"
#include "DataFormats/Provenance/interface/Parentage.h"
#include "DataFormats/Provenance/interface/ParentageRegistry.h"
#include "DataFormats/Provenance/interface/ProductProvenance.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/GetterOfProducts.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/ParameterSet/interface/ParameterWildcard.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "FWCore/Utilities/interface/RegexMatch.h"

#include <map>
#include <mutex>
#include <optional>
#include <regex>
#include <set>
#include <string>
#include <tuple>
#include <vector>

namespace {
  std::string quoted(std::string const& s) {
    std::string out = "\"";
    for (char c : s) {
      if (c == '"' || c == '\\')
        out += '\\';
      out += c;
    }
    return out + "\"";
  }
}  // namespace

class PicoMetadataProducer : public edm::global::EDProducer<edm::BeginRunProducer, edm::EndRunProducer> {
public:
  explicit PicoMetadataProducer(edm::ParameterSet const& cfg)
      : provenanceName_(cfg.getParameter<std::string>("provenanceName")) {
    auto const& strings = cfg.getParameter<edm::ParameterSet>("strings");
    for (auto const& name : strings.getParameterNamesForType<std::string>()) {
      strings_.emplace_back(name, strings.getParameter<std::string>(name));
      produces<nanoaod::UniqueString, edm::InRun>(name);
    }
    if (provenanceName_.empty())
      return;

    // Only tables the output module keeps: consuming a table runs its producer.
    std::vector<std::regex> keep;
    for (auto const& pattern : cfg.getParameter<std::vector<std::string>>("tableLabels"))
      keep.emplace_back(edm::glob2reg(pattern));
    tables_ = edm::GetterOfProducts<nanoaod::FlatTable>(
        [keep](edm::ProductDescription const& d) {
          if (!d.produced())
            return false;
          for (auto const& re : keep)
            if (std::regex_match(d.moduleLabel(), re))
              return true;
          return false;
        },
        this);
    callWhenNewProductsRegistered(tables_);
    produces<nanoaod::UniqueString, edm::Transition::EndRun>(provenanceName_);
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    edm::ParameterSetDescription strings;
    strings.setComment("constant strings, one TObjString each in the output file");
    strings.addNode(edm::ParameterWildcard<std::string>("*", edm::RequireZeroOrMore, true));
    desc.add<edm::ParameterSetDescription>("strings", strings);
    desc.add<std::string>("provenanceName", "picoProvenance")
        ->setComment("name of the provenance string in the output file; empty: do not record it");
    desc.add<std::vector<std::string>>("tableLabels", {"*Table"})
        ->setComment("module-label patterns of the FlatTables to describe, as kept by the output module");
    descriptions.add("picoMetadataProducer", desc);
  }

  void produce(edm::StreamID, edm::Event& event, edm::EventSetup const&) const override {
    if (provenanceName_.empty())
      return;
    std::vector<edm::Handle<nanoaod::FlatTable>> handles;
    tables_.fillHandles(event, handles);

    std::lock_guard<std::mutex> guard(mutex_);
    if (frozen_)
      return;
    for (auto const& h : handles) {
      auto const* prov = h.provenance();
      tables_seen_[h->name()].insert({prov->moduleLabel(), prov->productInstanceName(), h->extension()});
      walk(event, prov->branchID());
    }
  }

  void globalBeginRunProduce(edm::Run& run, edm::EventSetup const&) const override {
    for (auto const& [name, value] : strings_)
      run.put(std::make_unique<nanoaod::UniqueString>(value), name);
  }

  void globalEndRunProduce(edm::Run& run, edm::EventSetup const&) const override {
    if (provenanceName_.empty())
      return;
    std::lock_guard<std::mutex> guard(mutex_);
    if (!frozen_)
      frozen_ = json(moduleDescription().processName());
    run.put(std::make_unique<nanoaod::UniqueString>(*frozen_), provenanceName_);
  }

private:
  // Record what the module behind a product of this process read, recursively.
  // Products are revisited only when their parentage changes.
  void walk(edm::Event const& event, edm::BranchID const& id) const {
    auto const& prov = event.getProvenance(id);
    auto const* pp = prov.productProvenance();
    if (!pp || !prov.productDescription().produced() || !visited_.insert({id, pp->parentageID()}).second)
      return;
    auto const* parentage = edm::ParentageRegistry::instance()->getMapped(pp->parentageID());
    auto& reads = modules_[prov.moduleLabel()];
    if (!parentage)
      return;
    for (auto const& parent : parentage->parents()) {
      try {
        auto const& stable = event.getStableProvenance(parent);
        // branch names end with a '.'; drop it
        std::string name = stable.branchName();
        if (!name.empty() && name.back() == '.')
          name.pop_back();
        reads.insert(name);
        if (stable.productDescription().produced())
          walk(event, parent);
      } catch (cms::Exception const&) {
        // a parent the registry no longer describes; nothing to follow
      }
    }
  }

  std::string json(std::string const& process) const {
    std::string out = "{\"version\":1,\"process\":";
    out += quoted(process);
    out += ",\"tables\":{";
    for (auto t = tables_seen_.begin(); t != tables_seen_.end(); ++t) {
      if (t != tables_seen_.begin())
        out += ',';
      out += quoted(t->first);
      out += ":[";
      for (auto w = t->second.begin(); w != t->second.end(); ++w) {
        auto const& [label, instance, extension] = *w;
        if (w != t->second.begin())
          out += ',';
        out += "{\"module\":";
        out += quoted(label);
        out += ",\"instance\":";
        out += quoted(instance);
        out += extension ? ",\"extension\":true}" : ",\"extension\":false}";
      }
      out += ']';
    }
    out += "},\"modules\":{";
    for (auto m = modules_.begin(); m != modules_.end(); ++m) {
      if (m != modules_.begin())
        out += ',';
      out += quoted(m->first);
      out += ":[";
      for (auto r = m->second.begin(); r != m->second.end(); ++r) {
        if (r != m->second.begin())
          out += ',';
        out += quoted(*r);
      }
      out += ']';
    }
    out += "}}";
    return out;
  }

  std::vector<std::pair<std::string, std::string>> strings_;
  std::string const provenanceName_;
  edm::GetterOfProducts<nanoaod::FlatTable> tables_;

  mutable std::mutex mutex_;
  mutable std::optional<std::string> frozen_;
  mutable std::map<std::string, std::set<std::tuple<std::string, std::string, bool>>> tables_seen_;
  mutable std::map<std::string, std::set<std::string>> modules_;
  mutable std::set<std::pair<edm::BranchID, edm::ParentageID>> visited_;
};

DEFINE_FWK_MODULE(PicoMetadataProducer);
