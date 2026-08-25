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
from pathlib import Path


def setup(args, config):
    """Load the external C++ Z+jet helper modules into ROOT/Cling."""

    cpp_dir = Path(__file__).resolve().parent / "cpp"
    builder_header = (
        cpp_dir / "zjet_rdf_builder.h"
    ).resolve()

    if not builder_header.is_file():
        raise FileNotFoundError(
            "Z+jet C++ helper not found: {}".format(
                builder_header
            )
        )

    # Use the absolute header path rather than relying on Cling's include
    # search path.  zjet_rdf_builder.h includes zjet_rdf_common.h with a
    # quoted include, so the preprocessor resolves that second header
    # relative to the builder header directory automatically.
    ROOT.gInterpreter.Declare(
        '#include "{}"'.format(
            builder_header.as_posix()
        )
    )


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

        # ======================================================
        # Nominal / conventional Z+jet baseline
        #
        # Scalar columns are kept for debugging / selections.
        #
        # IMPORTANT:
        # Do NOT fill a sentinel such as -1 into a TProfile when no
        # nominal recoil jet exists.  For histogramming we expose
        # one-element RVecs for valid nominal Z+jet events and empty
        # RVecs otherwise.  RDataFrame then contributes zero entries
        # for events without a nominal recoil jet.
        #
        # The nominal jet is the highest-pT accepted jet in the
        # parallel recoil window. Since DB = pT(jet)/pT(Z), this is
        # equivalent to Max(dbParallel).
        # ======================================================

        .Define(
            "NominalJet_valid",
            "!zjet_result.ptParallel.empty()"
        )

        .Define(
            "NominalJet_index",
            """
            NominalJet_valid
                ? static_cast<int>(
                    ROOT::VecOps::ArgMax(
                        zjet_result.ptParallel
                    )
                  )
                : -1
            """
        )

        .Define(
            "DB_nominal",
            """
            NominalJet_valid
                ? zjet_result.dbParallel[NominalJet_index]
                : -1.f
            """
        )

        .Define(
            "Probe_pt_nominal",
            """
            NominalJet_valid
                ? zjet_result.ptParallel[NominalJet_index]
                : -1.f
            """
        )

        .Define(
            "DB_nominal_vec",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.dbParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "MPF_nominal_vec",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.nominalMPF
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Probe_pt_nominal_vec",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.ptParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Z_pt_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{zjet_result.Z_pt}
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_eta_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.etaParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_chHEF_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.chHEFParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_neHEF_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.neHEFParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_chEmEF_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.chEmEFParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_neEmEF_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.neEmEFParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "Jet_muEF_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{
                    zjet_result.muEFParallel[NominalJet_index]
                  }
                : ROOT::VecOps::RVec<float>{}
            """
        )

        .Define(
            "weight_nominal",
            """
            NominalJet_valid
                ? ROOT::VecOps::RVec<float>{zjet_eventWeight}
                : ROOT::VecOps::RVec<float>{}
            """
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

    return df


def get_regions(sample, args, config):

    # Keep the common zjet region independent of NominalJet_valid.
    #
    # The windowed method is allowed to construct its signal/control
    # estimator without requiring a conventional nominal recoil jet.
    # Nominal DB/MPF histograms are gated through the empty-RVec columns
    # DB_nominal_vec / MPF_nominal_vec / Z_pt_nominal / weight_nominal.
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
