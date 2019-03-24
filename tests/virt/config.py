from tests.config import *  # noqa: F401

# VIRT namespace
VIRT_NS = "cnv-virt-ns"

#COMMANDS
CHECK_DMIDECODE_PACKAGE = "sudo dmidecode -s baseboard-manufacturer | grep 'Radical Edward' | wc -l\n"
