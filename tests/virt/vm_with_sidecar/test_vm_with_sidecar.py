# -*- coding: utf-8 -*-

"""
VM with sidecar
"""
import logging
import pytest

from utilities import console
from tests.virt import config
from tests.virt.fixtures import create_vmi_with_yaml  # noqa: F401


LOGGER = logging.getLogger(__name__)


class TestVMWithSidecar(object):
    """
    Test VM with sidecar
    """
    vm_name = "vmi-with-sidecar-hook"
    vm_yaml = "tests/manifests/virt/vm_with_sidecar.yaml"

    @pytest.mark.usefixtures(create_vmi_with_yaml.__name__)
    def test_vm_with_sidecar_hook(self):
        """
        Test VM with sidecar hook, Install dmidecode with annotation
        smbios.vm.kubevirt.io/baseBoardManufacturer: "Radical Edward"
        And check that package includes manufacturer: "Radical Edward"
        """
        with console.Console(
            vm=self.vm_name, distro=config.FEDORA_VM,  namespace=config.VIRT_NS
        ) as vm_console:
            vm_console.sendline(config.CHECK_DMIDECODE_PACKAGE)
            vm_console.expect("1", timeout=20)
