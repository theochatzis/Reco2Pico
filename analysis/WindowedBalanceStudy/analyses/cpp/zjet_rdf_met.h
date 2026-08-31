#pragma once

#include "zjet_rdf_common.h"

namespace zjet_rdf {

/*
 * Rebuild the Type-I PUPPI MET used by the zjet all-pairs code:
 *
 *   MET_T1 = RawPuppiMET
 *            + sum_j pT_raw(j)
 *            - sum_j pT_corr(j)
 *
 * for lepton-cleaned jets with corrected pT > 15 GeV.
 *
 * Here Jet_pt is taken as the already-corrected jet pT present in Pico.
 * Jet_rawFactor is assumed to follow the NanoAOD convention:
 *
 *   rawPt = Jet_pt * (1 - Jet_rawFactor)
 *
 * No Tight Jet ID is applied to the Type-I sum, matching zjet.C.
 *
 * IMPORTANT:
 * The reference branch locally recomputes JEC/JER before this step.
 * This WindowedBalanceStudy synchronization intentionally does not add
 * that extra correction layer yet; it uses the corrected Pico Jet_pt.
 */
template <typename TRawFactor>
RebuiltMet rebuildPuppiMet(
    float rawPuppiMetPt,
    float rawPuppiMetPhi,

    const RVec<float>& jetPt,
    const RVec<float>& jetEta,
    const RVec<float>& jetPhi,
    const RVec<TRawFactor>& jetRawFactor,

    const P4& muPlus,
    const P4& muMinus
) {
    RebuiltMet result;

    if (
        !std::isfinite(rawPuppiMetPt) ||
        !std::isfinite(rawPuppiMetPhi)
    ) {
        return result;
    }

    double metPx =
        rawPuppiMetPt
        * std::cos(
            rawPuppiMetPhi
        );

    double metPy =
        rawPuppiMetPt
        * std::sin(
            rawPuppiMetPhi
        );

    for (
        std::size_t i = 0;
        i < jetPt.size();
        ++i
    ) {
        // Same 0.3 lepton cleaning used by the synchronized
        // zjet legacy/all-pairs recoil construction.
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
            <= TYPE1_JET_PT_MIN
        ) {
            continue;
        }

        const double rawPt =
            jetPt[i]
            * (
                1.0
                - static_cast<double>(
                    jetRawFactor[i]
                )
            );

        if (
            !std::isfinite(rawPt)
            || rawPt < 0.0
        ) {
            continue;
        }

        const double c = std::cos(jetPhi[i]);

        const double s = std::sin(jetPhi[i]);

        // Raw MET + raw jet - corrected jet.
        metPx += ( rawPt - jetPt[i] ) * c;

        metPy += ( rawPt - jetPt[i] ) * s;
    }

    result.valid = true;

    result.pt = static_cast<float>(
        std::hypot(
            metPx,
            metPy
        )
    );

    result.phi = static_cast<float>(
        std::atan2(
            metPy,
            metPx
        )
    );

    return result;
}


inline double standardMpf(
    const RebuiltMet& met,
    const P4& z
) {
    if (
        !met.valid
        || z.Pt() <= 0.0
    ) {
        return -999.0;
    }

    return (
        1.0
        + (
            met.pt
            / z.Pt()
        )
        * std::cos(
            deltaPhi(
                met.phi,
                z.Phi()
            )
        )
    );
}

} // namespace zjet_rdf
