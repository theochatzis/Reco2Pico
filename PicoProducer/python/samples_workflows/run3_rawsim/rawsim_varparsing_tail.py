# --- samples_workflows: VarParsing tail (run3_rawsim) ----------------------
# Appended by make_rawsim_cfgs.sh to the cmsDriver RECO cfg (the marker line
# above keeps it idempotent). See common/varparsing.py for the command-line
# contract: inputFiles= secondaryInputFiles= maxEvents= skipEvents= output=.
from Reco2Pico.PicoProducer.samples_workflows.common.varparsing import apply_varparsing
process = apply_varparsing(process, tag='run3_rawsim')
# --- end samples_workflows VarParsing tail ---------------------------------
