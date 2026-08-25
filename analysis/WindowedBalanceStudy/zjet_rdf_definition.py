"""
Z+jet RDataFrame analysis following the core windowed selection in zjet.C.

Compared with the previous windowed example, this version also stores
jet-composition fractions for every jet sampled in the:

  * parallel / signal window
  * transverse (+/-90 degree) control windows
  * signed windowed = signal - transverse collection

Fractions exposed:
  Jet_chHEF  : charged-hadron energy fraction
  Jet_neHEF  : neutral-hadron energy fraction
  Jet_chEmEF : charged electromagnetic energy fraction
  Jet_neEmEF : neutral electromagnetic energy fraction
  Jet_muEF   : muon energy fraction

Jet_jetId is intentionally NOT used. The Run-3 Tight PF Jet ID is
reconstructed explicitly, as in zjet.C.
"""

import ROOT


CPP_HELPERS = r"""
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


template <
    typename TMedium,
    typename TTight,
    typename TIso,
    typename TChMult,
    typename TNeMult,
    typename TNConst
>
Result build(
    const RVec<float>& muPt,
    const RVec<float>& muEta,
    const RVec<float>& muPhi,
    const RVec<float>& muMass,
    const RVec<int>& muCharge,
    const RVec<TMedium>& muMediumId,
    const RVec<TTight>& muTightId,
    const RVec<TIso>& muPfIsoId,

    const RVec<float>& jetPt,
    const RVec<float>& jetEta,
    const RVec<float>& jetPhi,

    const RVec<float>& jetChHEF,
    const RVec<float>& jetNeHEF,
    const RVec<float>& jetChEmEF,
    const RVec<float>& jetNeEmEF,
    const RVec<float>& jetMuEF,

    const RVec<TChMult>& jetChMultiplicity,
    const RVec<TNeMult>& jetNeMultiplicity,
    const RVec<TNConst>& jetNConstituents,

    float puppiMetPt,
    float puppiMetPhi
) {
    Result result;


    // ========================================================
    // 1. Nominal dimuon pair.
    //
    // Equivalent to:
    //   selectMuonPair(2, 2, 10., 27., true, ...)
    //
    // Both muons:
    //   mediumId
    //   pfIsoId >= 2
    //   pT > 10 GeV
    //   |eta| < 2.4
    //
    // Pair:
    //   opposite sign
    //   leading pT > 27 GeV
    //   >=1 tight + tight-isolation tag above 27 GeV
    //   choose pair closest to mZ
    // ========================================================

    int bestPlus = -1;
    int bestMinus = -1;
    double bestDistance = std::numeric_limits<double>::max();

    auto passProbeMuon = [&](std::size_t i) {
        return (
            static_cast<bool>(muMediumId[i]) &&
            static_cast<int>(muPfIsoId[i]) >= 2 &&
            muPt[i] > 10.f &&
            std::abs(muEta[i]) < 2.4f
        );
    };

    auto isTagMuon = [&](std::size_t i) {
        return (
            muPt[i] > 27.f &&
            static_cast<bool>(muTightId[i]) &&
            static_cast<int>(muPfIsoId[i]) >= 4
        );
    };

    for (std::size_t ip = 0; ip < muPt.size(); ++ip) {

        if (muCharge[ip] <= 0 || !passProbeMuon(ip))
            continue;

        const P4 plus(
            muPt[ip],
            muEta[ip],
            muPhi[ip],
            muMass[ip]
        );

        for (std::size_t im = 0; im < muPt.size(); ++im) {

            if (muCharge[im] >= 0 || !passProbeMuon(im))
                continue;

            const P4 minus(
                muPt[im],
                muEta[im],
                muPhi[im],
                muMass[im]
            );

            if (std::max(plus.Pt(), minus.Pt()) <= 27.)
                continue;

            if (!isTagMuon(ip) && !isTagMuon(im))
                continue;

            const double distance =
                std::abs((plus + minus).M() - MZ);

            if (distance < bestDistance) {
                bestDistance = distance;
                bestPlus = static_cast<int>(ip);
                bestMinus = static_cast<int>(im);
            }
        }
    }

    if (bestPlus < 0 || bestMinus < 0)
        return result;


    const P4 plus(
        muPt[bestPlus],
        muEta[bestPlus],
        muPhi[bestPlus],
        muMass[bestPlus]
    );

    const P4 minus(
        muPt[bestMinus],
        muEta[bestMinus],
        muPhi[bestMinus],
        muMass[bestMinus]
    );

    const P4 z = plus + minus;

    result.hasZ = true;
    result.Z_mass = z.M();
    result.Z_pt = z.Pt();
    result.Z_eta = z.Eta();
    result.Z_phi = z.Phi();

    if (z.Pt() <= 0.)
        return result;


    // ========================================================
    // 2. Signal and transverse directions.
    // ========================================================

    const double signalPhi =
        wrapPhi(z.Phi() + PI);

    const double plus90ProbePhi =
        wrapPhi(z.Phi() + 0.5*PI);

    const double minus90ProbePhi =
        wrapPhi(z.Phi() - 0.5*PI);

    // Axis opposite each transverse probe.
    const double plus90AxisPhi =
        wrapPhi(z.Phi() - 0.5*PI);

    const double minus90AxisPhi =
        wrapPhi(z.Phi() + 0.5*PI);


    auto leptonClear = [&](double probePhi) {
        return (
            std::abs(deltaPhi(probePhi, plus.Phi()))
                >= LEPTON_VETO_HALF_WIDTH &&
            std::abs(deltaPhi(probePhi, minus.Phi()))
                >= LEPTON_VETO_HALF_WIDTH
        );
    };


    result.signalClear =
        leptonClear(signalPhi);

    result.plus90Valid =
        result.signalClear &&
        leptonClear(plus90ProbePhi);

    result.minus90Valid =
        result.signalClear &&
        leptonClear(minus90ProbePhi);


    // Exact acceptance weighting currently used in zjet.C.
    result.signalAcceptance =
        0.5f * (
            (result.plus90Valid  ? 1.f : 0.f) +
            (result.minus90Valid ? 1.f : 0.f)
        );


    // ========================================================
    // 3. Standard event MPF.
    //
    //   MPF = 1 + MET . pT(Z) / pT(Z)^2
    // ========================================================

    const double nominalMPF =
        1.0 +
        (puppiMetPt / z.Pt()) *
        std::cos(deltaPhi(puppiMetPhi, z.Phi()));

    result.nominalMPF = nominalMPF;


    if (result.signalAcceptance == 0.f)
        return result;


    // ========================================================
    // 4. Jet loop.
    // ========================================================

    for (std::size_t i = 0; i < jetPt.size(); ++i) {

        if (!passTightJetId(
                i,
                jetEta,
                jetNeHEF,
                jetNeEmEF,
                jetChHEF,
                jetChMultiplicity,
                jetNeMultiplicity,
                jetNConstituents
            ))
            continue;


        if (deltaR(
                jetEta[i], jetPhi[i],
                plus.Eta(), plus.Phi()
            ) <= 0.2)
            continue;


        if (deltaR(
                jetEta[i], jetPhi[i],
                minus.Eta(), minus.Phi()
            ) <= 0.2)
            continue;


        const double db =
            jetPt[i] / z.Pt();


        // Same individual-jet balance range used in zjet.C.
        if (db <= 0.5 || db >= 2.0)
            continue;


        // ====================================================
        // Parallel / signal window.
        // ====================================================

        if (
            std::abs(
                deltaPhi(jetPhi[i], signalPhi)
            ) < WINDOW_HALF_WIDTH
        ) {
            const float w =
                result.signalAcceptance;

            result.dbParallel.push_back(db);
            result.mpfParallel.push_back(nominalMPF);

            result.ptParallel.push_back(jetPt[i]);
            result.etaParallel.push_back(jetEta[i]);
            result.phiParallel.push_back(jetPhi[i]);
            result.zptParallel.push_back(z.Pt());

            result.chHEFParallel.push_back(jetChHEF[i]);
            result.neHEFParallel.push_back(jetNeHEF[i]);
            result.chEmEFParallel.push_back(jetChEmEF[i]);
            result.neEmEFParallel.push_back(jetNeEmEF[i]);
            result.muEFParallel.push_back(jetMuEF[i]);

            result.wParallel.push_back(w);


            // Same positive contribution to the signed
            // sideband-subtracted collection.
            result.dbWindowed.push_back(db);
            result.mpfWindowed.push_back(nominalMPF);

            result.ptWindowed.push_back(jetPt[i]);
            result.etaWindowed.push_back(jetEta[i]);
            result.phiWindowed.push_back(jetPhi[i]);
            result.zptWindowed.push_back(z.Pt());

            result.chHEFWindowed.push_back(jetChHEF[i]);
            result.neHEFWindowed.push_back(jetNeHEF[i]);
            result.chEmEFWindowed.push_back(jetChEmEF[i]);
            result.neEmEFWindowed.push_back(jetNeEmEF[i]);
            result.muEFWindowed.push_back(jetMuEF[i]);

            result.wWindowed.push_back(w);
        }


        // ====================================================
        // +/- 90 degree transverse windows.
        // ====================================================

        const bool valid[2] = {
            result.plus90Valid,
            result.minus90Valid
        };

        const double probePhi[2] = {
            plus90ProbePhi,
            minus90ProbePhi
        };

        const double axisPhi[2] = {
            plus90AxisPhi,
            minus90AxisPhi
        };


        for (int idir = 0; idir < 2; ++idir) {

            if (!valid[idir])
                continue;


            if (
                std::abs(
                    deltaPhi(jetPhi[i], probePhi[idir])
                ) >= WINDOW_HALF_WIDTH
            )
                continue;


            // Same transverse MPF construction as zjet.C.
            const double transverseProjection =
                (puppiMetPt / z.Pt()) *
                std::cos(
                    deltaPhi(
                        puppiMetPhi,
                        axisPhi[idir]
                    )
                );

            const double mpfT =
                1.0 +
                transverseProjection +
                (nominalMPF - 1.0);


            // Positive control sample.
            result.dbTransverse.push_back(db);
            result.mpfTransverse.push_back(mpfT);

            result.ptTransverse.push_back(jetPt[i]);
            result.etaTransverse.push_back(jetEta[i]);
            result.phiTransverse.push_back(jetPhi[i]);
            result.zptTransverse.push_back(z.Pt());

            result.chHEFTransverse.push_back(jetChHEF[i]);
            result.neHEFTransverse.push_back(jetNeHEF[i]);
            result.chEmEFTransverse.push_back(jetChEmEF[i]);
            result.neEmEFTransverse.push_back(jetNeEmEF[i]);
            result.muEFTransverse.push_back(jetMuEF[i]);

            result.wTransverse.push_back(0.5f);


            // Negative transverse contribution in the
            // sideband-subtracted collection.
            result.dbWindowed.push_back(db);
            result.mpfWindowed.push_back(mpfT);

            result.ptWindowed.push_back(jetPt[i]);
            result.etaWindowed.push_back(jetEta[i]);
            result.phiWindowed.push_back(jetPhi[i]);
            result.zptWindowed.push_back(z.Pt());

            result.chHEFWindowed.push_back(jetChHEF[i]);
            result.neHEFWindowed.push_back(jetNeHEF[i]);
            result.chEmEFWindowed.push_back(jetChEmEF[i]);
            result.neEmEFWindowed.push_back(jetNeEmEF[i]);
            result.muEFWindowed.push_back(jetMuEF[i]);

            result.wWindowed.push_back(-0.5f);
        }
    }


    return result;
}

} // namespace zjet_rdf
"""


def setup(args, config):
    ROOT.gInterpreter.Declare(CPP_HELPERS)


def define_columns(df, sample, args, config):

    columns = {str(c) for c in df.GetColumnNames()}

    if "genWeight" in columns:
        df = df.Define(
            "zjet_eventWeight",
            "genWeight >= 0.f ? 1.f : -1.f"
        )
    else:
        df = df.Define(
            "zjet_eventWeight",
            "1.f"
        )


    df = (
        df

        .Define(
            "zjet_result",
            """
            zjet_rdf::build(
                Muon_pt,
                Muon_eta,
                Muon_phi,
                Muon_mass,
                Muon_charge,
                Muon_mediumId,
                Muon_tightId,
                Muon_pfIsoId,

                Jet_pt,
                Jet_eta,
                Jet_phi,

                Jet_chHEF,
                Jet_neHEF,
                Jet_chEmEF,
                Jet_neEmEF,
                Jet_muEF,

                Jet_chMultiplicity,
                Jet_neMultiplicity,
                Jet_nConstituents,

                PuppiMET_pt,
                PuppiMET_phi
            )
            """
        )

        # -----------------------
        # Z
        # -----------------------
        .Define("Z_valid", "zjet_result.hasZ")
        .Define("Z_mass", "zjet_result.Z_mass")
        .Define("Z_pt", "zjet_result.Z_pt")
        .Define("Z_eta", "zjet_result.Z_eta")
        .Define("Z_phi", "zjet_result.Z_phi")

        .Define(
            "Z_signalAcceptance",
            "zjet_result.signalAcceptance"
        )

        .Define(
            "MPF_nominal",
            "zjet_result.nominalMPF"
        )

        .Define(
            "DB_nominal",
            "zjet_result.dbParallel.empty() ? -1.f : "
            "ROOT::VecOps::Max(zjet_result.dbParallel)"
        )


        # ======================================================
        # Parallel / signal sample
        # ======================================================

        .Define(
            "DB_parallel",
            "zjet_result.dbParallel"
        )
        .Define(
            "MPF_parallel",
            "zjet_result.mpfParallel"
        )

        .Define(
            "Jet_pt_parallel",
            "zjet_result.ptParallel"
        )
        .Define(
            "Jet_eta_parallel",
            "zjet_result.etaParallel"
        )
        .Define(
            "Jet_phi_parallel",
            "zjet_result.phiParallel"
        )
        .Define(
            "Z_pt_parallel",
            "zjet_result.zptParallel"
        )

        .Define(
            "Jet_chHEF_parallel",
            "zjet_result.chHEFParallel"
        )
        .Define(
            "Jet_neHEF_parallel",
            "zjet_result.neHEFParallel"
        )
        .Define(
            "Jet_chEmEF_parallel",
            "zjet_result.chEmEFParallel"
        )
        .Define(
            "Jet_neEmEF_parallel",
            "zjet_result.neEmEFParallel"
        )
        .Define(
            "Jet_muEF_parallel",
            "zjet_result.muEFParallel"
        )

        .Define(
            "weight_parallel",
            "zjet_eventWeight * zjet_result.wParallel"
        )


        # ======================================================
        # Transverse control sample
        # ======================================================

        .Define(
            "DB_transverse",
            "zjet_result.dbTransverse"
        )
        .Define(
            "MPF_transverse",
            "zjet_result.mpfTransverse"
        )

        .Define(
            "Jet_pt_transverse",
            "zjet_result.ptTransverse"
        )
        .Define(
            "Jet_eta_transverse",
            "zjet_result.etaTransverse"
        )
        .Define(
            "Jet_phi_transverse",
            "zjet_result.phiTransverse"
        )
        .Define(
            "Z_pt_transverse",
            "zjet_result.zptTransverse"
        )

        .Define(
            "Jet_chHEF_transverse",
            "zjet_result.chHEFTransverse"
        )
        .Define(
            "Jet_neHEF_transverse",
            "zjet_result.neHEFTransverse"
        )
        .Define(
            "Jet_chEmEF_transverse",
            "zjet_result.chEmEFTransverse"
        )
        .Define(
            "Jet_neEmEF_transverse",
            "zjet_result.neEmEFTransverse"
        )
        .Define(
            "Jet_muEF_transverse",
            "zjet_result.muEFTransverse"
        )

        .Define(
            "weight_transverse",
            "zjet_eventWeight * zjet_result.wTransverse"
        )


        # ======================================================
        # Signed windowed collection
        # ======================================================

        .Define(
            "DB_windowed",
            "zjet_result.dbWindowed"
        )
        .Define(
            "MPF_windowed",
            "zjet_result.mpfWindowed"
        )

        .Define(
            "Jet_pt_windowed",
            "zjet_result.ptWindowed"
        )
        .Define(
            "Jet_eta_windowed",
            "zjet_result.etaWindowed"
        )
        .Define(
            "Jet_phi_windowed",
            "zjet_result.phiWindowed"
        )
        .Define(
            "Z_pt_windowed",
            "zjet_result.zptWindowed"
        )

        .Define(
            "Jet_chHEF_windowed",
            "zjet_result.chHEFWindowed"
        )
        .Define(
            "Jet_neHEF_windowed",
            "zjet_result.neHEFWindowed"
        )
        .Define(
            "Jet_chEmEF_windowed",
            "zjet_result.chEmEFWindowed"
        )
        .Define(
            "Jet_neEmEF_windowed",
            "zjet_result.neEmEFWindowed"
        )
        .Define(
            "Jet_muEF_windowed",
            "zjet_result.muEFWindowed"
        )

        .Define(
            "weight_windowed",
            "zjet_eventWeight * zjet_result.wWindowed"
        )


        # Counts
        .Define(
            "nParallelWindowJets",
            "static_cast<int>(zjet_result.dbParallel.size())"
        )
        .Define(
            "nTransverseWindowJets",
            "static_cast<int>(zjet_result.dbTransverse.size())"
        )
    )

    # ======================================================
    # |eta| slices for jet-composition profiles
    #
    # These are generated here rather than hard-coding a large
    # number of C++ vectors in Result. Every masked vector keeps
    # Z pT, the jet fraction and the corresponding weight aligned.
    # ======================================================
    eta_regions = [
        ("eta0to1p3",   0.0, 1.3),
        ("eta1p3to1p5", 1.3, 1.5),
        ("eta1p5to2p5", 1.5, 2.5),
        ("eta2p5to2p7", 2.5, 2.7),
        ("eta2p7to3p0", 2.7, 3.0),
        ("eta3p0to5p0", 3.0, 5.0),
    ]

    fractions = [
        "Jet_chHEF",
        "Jet_neHEF",
        "Jet_chEmEF",
        "Jet_neEmEF",
        "Jet_muEF",
    ]

    samples = [
        "parallel",
        "transverse",
        "windowed",
    ]

    for sample_name in samples:
        eta_column = f"Jet_eta_{sample_name}"

        for region_name, eta_min, eta_max in eta_regions:
            mask_name = f"mask_{sample_name}_{region_name}"

            df = df.Define(
                mask_name,
                (
                    f"(ROOT::VecOps::abs({eta_column}) >= {eta_min}f) && "
                    f"(ROOT::VecOps::abs({eta_column}) < {eta_max}f)"
                )
            )

            df = df.Define(
                f"Z_pt_{sample_name}_{region_name}",
                f"Z_pt_{sample_name}[{mask_name}]"
            )

            df = df.Define(
                f"weight_{sample_name}_{region_name}",
                f"weight_{sample_name}[{mask_name}]"
            )

            for fraction in fractions:
                source = f"{fraction}_{sample_name}"
                target = f"{fraction}_{sample_name}_{region_name}"

                df = df.Define(
                    target,
                    f"{source}[{mask_name}]"
                )

    return df


def get_regions(sample, args, config):

    return {
        "zjet": {
            "cuts": [
                (
                    "Flag_goodVertices && "
                    "Flag_globalSuperTightHalo2016Filter && "
                    "Flag_EcalDeadCellTriggerPrimitiveFilter && "
                    "Flag_BadPFMuonFilter && "
                    "Flag_BadPFMuonDzFilter && "
                    "Flag_hfNoisyHitsFilter && "
                    "Flag_eeBadScFilter && "
                    "Flag_ecalBadCalibFilter"
                ),

                "HLT_IsoMu24",

                "Z_valid",

                # |m_mumu - 91.188| < 1.5 * Gamma_Z
                "abs(Z_mass - 91.1880f) < 3.74325f",

                # Exact paired-sideband acceptance convention
                # currently used in zjet.C.
                "Z_signalAcceptance > 0.f",
            ]
        }
    }
