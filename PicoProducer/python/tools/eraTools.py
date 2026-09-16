def getEra(name):

    from Configuration.Eras.Era_Run3_cff import Run3
    from Configuration.Eras.Era_Run3_2024_cff import Run3_2024
    from Configuration.Eras.Era_Run3_2025_cff import Run3_2025

    eras = {
        "Run3": Run3,
        "Run3_2024": Run3_2024,
        "Run3_2025": Run3_2025,
    }

    if name not in eras:
        raise ValueError(
            "Unknown era '{}'. Available: {}".format(
                name,
                ", ".join(sorted(eras)),
            )
        )

    return eras[name]