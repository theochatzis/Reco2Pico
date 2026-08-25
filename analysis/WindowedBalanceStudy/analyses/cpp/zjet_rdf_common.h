#pragma once

// Common C++ definitions for the Z+jet RDataFrame analysis.
//
// Keep lightweight utilities, constants, object selection helpers and the
// Result data structure here.  The event-building algorithm lives in
// zjet_rdf_builder.h.

#include <ROOT/RVec.hxx>
#include <Math/Vector4D.h>

#include <algorithm>
#include <cmath>
#include <limits>

namespace zjet_rdf {

using ROOT::VecOps::RVec;
using P4 = ROOT::Math::PtEtaPhiMVector;

constexpr double PI = 3.14159265358979323846;
constexpr double MZ = 91.1880;
constexpr double GAMMA_Z = 2.4955;
constexpr double Z_MASS_HALF_WINDOW = 1.5 * GAMMA_Z;
constexpr double WINDOW_HALF_WIDTH = PI / 16.0;
constexpr double LEPTON_VETO_HALF_WIDTH = PI / 8.0;


inline double deltaPhi(double phi1, double phi2) {
    return std::remainder(phi1 - phi2, 2.0 * PI);
}


inline double deltaR(
    double eta1, double phi1,
    double eta2, double phi2
) {
    const double deta = eta1 - eta2;
    const double dphi = deltaPhi(phi1, phi2);
    return std::sqrt(deta*deta + dphi*dphi);
}


inline double wrapPhi(double phi) {
    return std::remainder(phi, 2.0 * PI);
}


// ------------------------------------------------------------
// Run-3 Tight PF Jet ID reconstructed from jet composition.
// Same eta-dependent logic used in zjet.C.
// ------------------------------------------------------------

template <typename TChMult, typename TNeMult, typename TNConst>
bool passTightJetId(
    std::size_t i,
    const RVec<float>& eta,
    const RVec<float>& neHEF,
    const RVec<float>& neEmEF,
    const RVec<float>& chHEF,
    const RVec<TChMult>& chMultiplicity,
    const RVec<TNeMult>& neMultiplicity,
    const RVec<TNConst>& nConstituents
) {
    const double abseta = std::abs(eta[i]);

    if (abseta <= 2.6) {
        return (
            neHEF[i] < 0.99 &&
            neEmEF[i] < 0.90 &&
            nConstituents[i] > 1 &&
            chHEF[i] > 0.01 &&
            chMultiplicity[i] > 0
        );
    }

    if (abseta <= 2.7) {
        return (
            neHEF[i] < 0.90 &&
            neEmEF[i] < 0.99
        );
    }

    if (abseta <= 3.0) {
        return neHEF[i] < 0.99;
    }

    if (abseta < 5.0) {
        return (
            neEmEF[i] < 0.40 &&
            neMultiplicity[i] >= 2
        );
    }

    return false;
}


// ------------------------------------------------------------
// Result object.
// Every vector contains one element per sampled jet.
// ------------------------------------------------------------

struct Result {
    bool hasZ = false;
    bool signalClear = false;
    bool plus90Valid = false;
    bool minus90Valid = false;

    float Z_mass = -1.f;
    float Z_pt = -1.f;
    float Z_eta = -99.f;
    float Z_phi = 0.f;

    float signalAcceptance = 0.f;
    float nominalMPF = -999.f;

    // -----------------------
    // Parallel / signal jets
    // -----------------------
    RVec<float> dbParallel;
    RVec<float> mpfParallel;

    RVec<float> ptParallel;
    RVec<float> etaParallel;
    RVec<float> phiParallel;
    RVec<float> zptParallel;

    RVec<float> chHEFParallel;
    RVec<float> neHEFParallel;
    RVec<float> chEmEFParallel;
    RVec<float> neEmEFParallel;
    RVec<float> muEFParallel;

    RVec<float> wParallel;

    // -----------------------
    // Transverse jets
    // Combined T+ and T- sample.
    // Each valid side contributes weight +0.5.
    // -----------------------
    RVec<float> dbTransverse;
    RVec<float> mpfTransverse;

    RVec<float> ptTransverse;
    RVec<float> etaTransverse;
    RVec<float> phiTransverse;
    RVec<float> zptTransverse;

    RVec<float> chHEFTransverse;
    RVec<float> neHEFTransverse;
    RVec<float> chEmEFTransverse;
    RVec<float> neEmEFTransverse;
    RVec<float> muEFTransverse;

    RVec<float> wTransverse;

    // -----------------------
    // Signed sideband-subtracted collection:
    //
    //   signal contribution     : +signalAcceptance
    //   each transverse sideband: -0.5
    //
    // This preserves the exact paired-acceptance convention
    // currently used in zjet.C.
    // -----------------------
    RVec<float> dbWindowed;
    RVec<float> mpfWindowed;

    RVec<float> ptWindowed;
    RVec<float> etaWindowed;
    RVec<float> phiWindowed;
    RVec<float> zptWindowed;

    RVec<float> chHEFWindowed;
    RVec<float> neHEFWindowed;
    RVec<float> chEmEFWindowed;
    RVec<float> neEmEFWindowed;
    RVec<float> muEFWindowed;

    RVec<float> wWindowed;
};

} // namespace zjet_rdf
