import ROOT

f = ROOT.TFile.Open("/eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico.root")
t = f.Get("Events")

for iev in range(5):
    t.GetEntry(iev)

    vals = {}
    for i in range(len(t.PFRhoStrip_etaBin)):
        eb = int(t.PFRhoStrip_etaBin[i])
        if abs(eb) == 29:
            vals.setdefault(eb, 0)
            vals[eb] += int(t.PFRhoStrip_n[i])

    print("event", iev, vals)


t.GetEntry(0)

seen = {}

for i in range(len(t.PFRhoStrip_etaBin)):
    eb = int(t.PFRhoStrip_etaBin[i])
    if abs(eb) == 29:
        key = (eb, int(t.PFRhoStrip_phiBin[i]))
        if key not in seen:
            seen[key] = (
                float(t.PFRhoStrip_etaMin[i]),
                float(t.PFRhoStrip_etaMax[i]),
                float(t.PFRhoStrip_eta[i]),
                float(t.PFRhoStrip_phi[i]),
                float(t.PFRhoStrip_dPhi[i]),
            )

for key in sorted(seen):
    eb, pb = key
    emin, emax, eta, phi, dphi = seen[key]
    print(
        f"etaBin {eb:3d}, phiBin {pb:3d}: "
        f"{emin: .4f} < eta < {emax: .4f}, "
        f"eta={eta: .4f}, phi={phi: .4f}, dPhi={dphi:.4f}"
    )
