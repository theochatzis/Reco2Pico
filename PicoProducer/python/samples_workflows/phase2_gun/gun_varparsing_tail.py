# --- samples_workflows: VarParsing tail (phase2_gun) -----------------------
# Appended by make_gun_cfgs.sh to every cfg of the chain (the marker line above
# lets sw_append_tail replace it). See common/varparsing.py for the command-line contract.
from Reco2Pico.PicoProducer.samples_workflows.common.varparsing import apply_varparsing
from Reco2Pico.PicoProducer.samples_workflows.phase2_gun.gun_options import GUN_OPTIONS, apply_gun, apply_gun_thresholds
process = apply_varparsing(process, extra_options=GUN_OPTIONS, on_gen=apply_gun, on_process=apply_gun_thresholds, tag='phase2_gun')
# --- end samples_workflows VarParsing tail ---------------------------------
