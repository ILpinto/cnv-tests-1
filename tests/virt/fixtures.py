import pytest
from tests.test_utils import wait_for_vm_interfaces
from resources.virtual_machine_instance import VirtualMachineInstance
from utilities import types
from . import config


@pytest.fixture()
def create_vmi_with_yaml(request):
    """
    create VMI and wait till it running with yaml (don't start VM unless it has running state True)
    """
    vm_name = request.cls.vm_name
    vm_yaml = request.cls.vm_yaml
    vmi = VirtualMachineInstance(name=vm_name, namespace=config.VIRT_NS)
    
    def fin():
        assert vmi.delete(wait=True)
    
    request.addfinalizer(fin)
    assert vmi.create(yaml_file=vm_yaml, wait=True)
    vmi.wait_for_status(status=types.RUNNING, timeout=60, sleep=10)
    wait_for_vm_interfaces(vmi, timeout=720)
