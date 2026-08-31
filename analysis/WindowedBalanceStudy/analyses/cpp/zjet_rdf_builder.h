#pragma once

#include "zjet_rdf_common.h"
#include "zjet_rdf_met.h"
#include "zjet_rdf_baseline.h"

namespace zjet_rdf {

template <
    typename TMedium,
    typename TTight,
    typename TIso,
    typename TChMult,
    typename TNeMult,
    typename TNConst,
    typename TRawFactor
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

    const RVec<TRawFactor>& jetRawFactor,

    float rawPuppiMetPt,
    float rawPuppiMetPhi
) {
    Result result;

    // ========================================================
    // 1. Keep the existing WindowedBalanceStudy Z selection.
    // ========================================================

    int bestPlus = -1;
    int bestMinus = -1;

    double bestDistance =
        std::numeric_limits<double>::max();

    auto passProbeMuon =
        [&](std::size_t i) {
            return (
                static_cast<bool>(
                    muMediumId[i]
                )
                && static_cast<int>(
                    muPfIsoId[i]
                ) >= 2
                && muPt[i] > 10.f
                && std::abs(
                    muEta[i]
                ) < 2.4f
            );
        };

    auto isTagMuon =
        [&](std::size_t i) {
            return (
                muPt[i] > 27.f
                && static_cast<bool>(
                    muTightId[i]
                )
                && static_cast<int>(
                    muPfIsoId[i]
                ) >= 4
            );
        };

    for (
        std::size_t ip = 0;
        ip < muPt.size();
        ++ip
    ) {
        if (
            muCharge[ip] <= 0
            || !passProbeMuon(
                ip
            )
        ) {
            continue;
        }

        const P4 plus(
            muPt[ip],
            muEta[ip],
            muPhi[ip],
            muMass[ip]
        );

        for (
            std::size_t im = 0;
            im < muPt.size();
            ++im
        ) {
            if (
                muCharge[im] >= 0
                || !passProbeMuon(
                    im
                )
            ) {
                continue;
            }

            const P4 minus(
                muPt[im],
                muEta[im],
                muPhi[im],
                muMass[im]
            );

            if (
                std::max(
                    plus.Pt(),
                    minus.Pt()
                ) <= 27.
            ) {
                continue;
            }

            if (
                !isTagMuon(
                    ip
                )
                && !isTagMuon(
                    im
                )
            ) {
                continue;
            }

            const double distance =
                std::abs(
                    (
                        plus
                        + minus
                    ).M()
                    - MZ
                );

            if (
                distance
                < bestDistance
            ) {
                bestDistance =
                    distance;

                bestPlus =
                    static_cast<int>(
                        ip
                    );

                bestMinus =
                    static_cast<int>(
                        im
                    );
            }
        }
    }

    if (
        bestPlus < 0
        || bestMinus < 0
    ) {
        return result;
    }

    const P4 plus(
        muPt[
            bestPlus
        ],
        muEta[
            bestPlus
        ],
        muPhi[
            bestPlus
        ],
        muMass[
            bestPlus
        ]
    );

    const P4 minus(
        muPt[
            bestMinus
        ],
        muEta[
            bestMinus
        ],
        muPhi[
            bestMinus
        ],
        muMass[
            bestMinus
        ]
    );

    const P4 z =
        plus + minus;

    result.hasZ = true;

    result.Z_mass =
        z.M();

    result.Z_pt =
        z.Pt();

    result.Z_eta =
        z.Eta();

    result.Z_phi =
        z.Phi();

    if (
        z.Pt() <= 0.
    ) {
        return result;
    }


    // ========================================================
    // 2. Rebuild PUPPI Type-I MET from RawPuppiMET.
    // ========================================================

    const RebuiltMet rebuiltMet =
        rebuildPuppiMet(
            rawPuppiMetPt,
            rawPuppiMetPhi,
            jetPt,
            jetEta,
            jetPhi,
            jetRawFactor,
            plus,
            minus
        );

    if (
        !rebuiltMet.valid
    ) {
        return result;
    }

    result.rebuiltPuppiMET_pt =
        rebuiltMet.pt;

    result.rebuiltPuppiMET_phi =
        rebuiltMet.phi;

    result.nominalMPF =
        standardMpf(
            rebuiltMet,
            z
        );


    // ========================================================
    // 3. Synchronized legacy/nominal baseline.
    // ========================================================

    result.baseline =
        buildBaseline(
            z,
            plus,
            minus,

            jetPt,
            jetEta,
            jetPhi,

            jetChHEF,
            jetNeHEF,
            jetChEmEF,
            jetNeEmEF,
            jetMuEF,

            rebuiltMet
        );


    // ========================================================
    // 4. Signal and transverse directions.
    // ========================================================

    const double signalPhi =
        wrapPhi(
            z.Phi()
            + PI
        );

    const double plus90ProbePhi =
        wrapPhi(
            z.Phi()
            + 0.5*PI
        );

    const double minus90ProbePhi =
        wrapPhi(
            z.Phi()
            - 0.5*PI
        );

    const double plus90AxisPhi =
        wrapPhi(
            z.Phi()
            - 0.5*PI
        );

    const double minus90AxisPhi =
        wrapPhi(
            z.Phi()
            + 0.5*PI
        );

    auto leptonClear =
        [&](double probePhi) {
            return (
                std::abs(
                    deltaPhi(
                        probePhi,
                        plus.Phi()
                    )
                )
                >= LEPTON_VETO_HALF_WIDTH

                &&

                std::abs(
                    deltaPhi(
                        probePhi,
                        minus.Phi()
                    )
                )
                >= LEPTON_VETO_HALF_WIDTH
            );
        };

    result.signalClear =
        leptonClear(
            signalPhi
        );

    result.plus90Valid =
        (
            result.signalClear
            && leptonClear(
                plus90ProbePhi
            )
        );

    result.minus90Valid =
        (
            result.signalClear
            && leptonClear(
                minus90ProbePhi
            )
        );

    result.signalAcceptance =
        0.5f
        * (
            (
                result.plus90Valid
                ? 1.f
                : 0.f
            )
            +
            (
                result.minus90Valid
                ? 1.f
                : 0.f
            )
        );

    if (
        result.signalAcceptance
        == 0.f
    ) {
        return result;
    }


    // ========================================================
    // 5. All-pairs/windowed jet loop.
    //
    // This part is intentionally unchanged except that all MPF
    // projections now use the rebuilt PUPPI MET.
    // ========================================================

    for (
        std::size_t i = 0;
        i < jetPt.size();
        ++i
    ) {
        if (
            !passTightJetId(
                i,
                jetEta,
                jetNeHEF,
                jetNeEmEF,
                jetChHEF,
                jetChMultiplicity,
                jetNeMultiplicity,
                jetNConstituents
            )
        ) {
            continue;
        }

        // Keep the existing all-pairs cleaning for now.
        if (
            deltaR(
                jetEta[i],
                jetPhi[i],
                plus.Eta(),
                plus.Phi()
            ) <= 0.2
        ) {
            continue;
        }

        if (
            deltaR(
                jetEta[i],
                jetPhi[i],
                minus.Eta(),
                minus.Phi()
            ) <= 0.2
        ) {
            continue;
        }

        const double db =
            jetPt[i]
            / z.Pt();

        if (
            db <= 0.5
            || db >= 2.0
        ) {
            continue;
        }

        if (
            std::abs(
                deltaPhi(
                    jetPhi[i],
                    signalPhi
                )
            )
            < WINDOW_HALF_WIDTH
        ) {
            const float w =
                result.signalAcceptance;

            result.dbParallel.push_back(
                db
            );

            result.mpfParallel.push_back(
                result.nominalMPF
            );

            result.ptParallel.push_back(
                jetPt[i]
            );

            result.etaParallel.push_back(
                jetEta[i]
            );

            result.phiParallel.push_back(
                jetPhi[i]
            );

            result.zptParallel.push_back(
                z.Pt()
            );

            result.chHEFParallel.push_back(
                jetChHEF[i]
            );

            result.neHEFParallel.push_back(
                jetNeHEF[i]
            );

            result.chEmEFParallel.push_back(
                jetChEmEF[i]
            );

            result.neEmEFParallel.push_back(
                jetNeEmEF[i]
            );

            result.muEFParallel.push_back(
                jetMuEF[i]
            );

            result.wParallel.push_back(
                w
            );

            result.dbWindowed.push_back(
                db
            );

            result.mpfWindowed.push_back(
                result.nominalMPF
            );

            result.ptWindowed.push_back(
                jetPt[i]
            );

            result.etaWindowed.push_back(
                jetEta[i]
            );

            result.phiWindowed.push_back(
                jetPhi[i]
            );

            result.zptWindowed.push_back(
                z.Pt()
            );

            result.chHEFWindowed.push_back(
                jetChHEF[i]
            );

            result.neHEFWindowed.push_back(
                jetNeHEF[i]
            );

            result.chEmEFWindowed.push_back(
                jetChEmEF[i]
            );

            result.neEmEFWindowed.push_back(
                jetNeEmEF[i]
            );

            result.muEFWindowed.push_back(
                jetMuEF[i]
            );

            result.wWindowed.push_back(
                w
            );
        }

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

        for (
            int idir = 0;
            idir < 2;
            ++idir
        ) {
            if (
                !valid[
                    idir
                ]
            ) {
                continue;
            }

            if (
                std::abs(
                    deltaPhi(
                        jetPhi[i],
                        probePhi[
                            idir
                        ]
                    )
                )
                >= WINDOW_HALF_WIDTH
            ) {
                continue;
            }

            const double transverseProjection =
                (
                    rebuiltMet.pt
                    / z.Pt()
                )
                * std::cos(
                    deltaPhi(
                        rebuiltMet.phi,
                        axisPhi[
                            idir
                        ]
                    )
                );

            const double mpfT =
                (
                    1.0
                    + transverseProjection
                    + (
                        result.nominalMPF
                        - 1.0
                    )
                );

            result.dbTransverse.push_back(
                db
            );

            result.mpfTransverse.push_back(
                mpfT
            );

            result.ptTransverse.push_back(
                jetPt[i]
            );

            result.etaTransverse.push_back(
                jetEta[i]
            );

            result.phiTransverse.push_back(
                jetPhi[i]
            );

            result.zptTransverse.push_back(
                z.Pt()
            );

            result.chHEFTransverse.push_back(
                jetChHEF[i]
            );

            result.neHEFTransverse.push_back(
                jetNeHEF[i]
            );

            result.chEmEFTransverse.push_back(
                jetChEmEF[i]
            );

            result.neEmEFTransverse.push_back(
                jetNeEmEF[i]
            );

            result.muEFTransverse.push_back(
                jetMuEF[i]
            );

            result.wTransverse.push_back(
                0.5f
            );

            result.dbWindowed.push_back(
                db
            );

            result.mpfWindowed.push_back(
                mpfT
            );

            result.ptWindowed.push_back(
                jetPt[i]
            );

            result.etaWindowed.push_back(
                jetEta[i]
            );

            result.phiWindowed.push_back(
                jetPhi[i]
            );

            result.zptWindowed.push_back(
                z.Pt()
            );

            result.chHEFWindowed.push_back(
                jetChHEF[i]
            );

            result.neHEFWindowed.push_back(
                jetNeHEF[i]
            );

            result.chEmEFWindowed.push_back(
                jetChEmEF[i]
            );

            result.neEmEFWindowed.push_back(
                jetNeEmEF[i]
            );

            result.muEFWindowed.push_back(
                jetMuEF[i]
            );

            result.wWindowed.push_back(
                -0.5f
            );
        }
    }

    return result;
}

} // namespace zjet_rdf
