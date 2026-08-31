#pragma once

#include "zjet_rdf_common.h"

namespace zjet_rdf {

/*
 * Legacy leading-jet baseline synchronized to the core definition in
 * miquork/zjet codex/all-pairs-zjet.
 *
 * Scope intentionally synchronized here:
 *
 *   - jets cleaned from the selected Z muons by DeltaR >= 0.3
 *   - candidate list starts at jet pT >= 10 GeV
 *   - leading jet requires pT >= 12 GeV and |eta| <= 5
 *   - leading jet is the highest-pT cleaned jet
 *   - back-to-back residual:
 *
 *       | |DeltaPhi(j1,Z)| - pi | < 0.44
 *
 *   - alpha:
 *
 *       alpha = pT(j2)/pT(Z)  if pT(j2) >= 15 GeV
 *               0             otherwise
 *
 *   - require alpha < 1
 *   - NO Tight Jet ID requirement for the baseline jet
 *
 * Intentionally not added in this first synchronization:
 *   - data jet-veto map
 *   - the legacy orientation-dependent forward-spike veto
 *   - local JEC/JER recomputation
 *   - synchronized dimuon trigger/selection
 */
BaselineResult buildBaseline(
    const P4& z,
    const P4& muPlus,
    const P4& muMinus,

    const RVec<float>& jetPt,
    const RVec<float>& jetEta,
    const RVec<float>& jetPhi,

    const RVec<float>& jetChHEF,
    const RVec<float>& jetNeHEF,
    const RVec<float>& jetChEmEF,
    const RVec<float>& jetNeEmEF,
    const RVec<float>& jetMuEF,

    const RebuiltMet& rebuiltMet
) {
    BaselineResult result;

    if (
        z.Pt() <= 0.0
        || !rebuiltMet.valid
    ) {
        return result;
    }

    std::vector<std::size_t> indices;
    indices.reserve(
        jetPt.size()
    );

    for (
        std::size_t i = 0;
        i < jetPt.size();
        ++i
    ) {
        if (
            deltaR(
                jetEta[i],
                jetPhi[i],
                muPlus.Eta(),
                muPlus.Phi()
            ) < BASELINE_CLEAN_DR
        ) {
            continue;
        }

        if (
            deltaR(
                jetEta[i],
                jetPhi[i],
                muMinus.Eta(),
                muMinus.Phi()
            ) < BASELINE_CLEAN_DR
        ) {
            continue;
        }

        if (
            jetPt[i]
            >= BASELINE_LIST_PT_MIN
        ) {
            indices.push_back(
                i
            );
        }
    }

    std::sort(
        indices.begin(),
        indices.end(),
        [&](std::size_t first, std::size_t second) {
            return (
                jetPt[first]
                > jetPt[second]
            );
        }
    );

    int leadingIndex = -1;

    for (
        const std::size_t index
        : indices
    ) {
        if (
            jetPt[index]
            >= BASELINE_LEADING_PT_MIN
            && std::abs(
                jetEta[index]
            ) <= BASELINE_MAX_ABS_ETA
        ) {
            leadingIndex =
                static_cast<int>(
                    index
                );

            break;
        }
    }

    if (
        leadingIndex < 0
    ) {
        return result;
    }

    const double dphi =
        std::abs(
            deltaPhi(
                jetPhi[
                    leadingIndex
                ],
                z.Phi()
            )
        );

    const double dphiResidual =
        std::abs(
            dphi - PI
        );

    if (
        dphiResidual
        >= BASELINE_DPHI_RESIDUAL_MAX
    ) {
        return result;
    }

    int subleadingIndex = -1;

    for (
        const std::size_t index
        : indices
    ) {
        if (
            static_cast<int>(
                index
            )
            == leadingIndex
        ) {
            continue;
        }

        subleadingIndex =
            static_cast<int>(
                index
            );

        break;
    }

    double alpha = 0.0;

    if (
        subleadingIndex >= 0
        && jetPt[
            subleadingIndex
        ] >= BASELINE_SECOND_PT_FOR_ALPHA
    ) {
        alpha =
            jetPt[
                subleadingIndex
            ]
            / z.Pt();
    }

    if (
        alpha >= 1.0
    ) {
        return result;
    }

    result.valid = true;

    result.leadingJetIndex =
        leadingIndex;

    result.subleadingJetIndex =
        subleadingIndex;

    result.jetPt =
        jetPt[
            leadingIndex
        ];

    result.jetEta =
        jetEta[
            leadingIndex
        ];

    result.jetPhi =
        jetPhi[
            leadingIndex
        ];

    result.db =
        result.jetPt
        / z.Pt();

    result.mpf =
        standardMpf(
            rebuiltMet,
            z
        );

    result.alpha =
        static_cast<float>(
            alpha
        );

    result.chHEF =
        jetChHEF[
            leadingIndex
        ];

    result.neHEF =
        jetNeHEF[
            leadingIndex
        ];

    result.chEmEF =
        jetChEmEF[
            leadingIndex
        ];

    result.neEmEF =
        jetNeEmEF[
            leadingIndex
        ];

    result.muEF =
        jetMuEF[
            leadingIndex
        ];

    return result;
}

} // namespace zjet_rdf
