# -*- coding: utf-8 -*-

"""
VM to VM connectivity
"""
import logging
import sys

import pytest

from utilities import client
from . import config
from utilities import console
from utilities import utils
from .fixtures import prepare_env  # noqa: F401


LOGGER = logging.getLogger(__name__)


class TestConnectivity(object):
    """
    Test VM to VM connectivity
    """
    api = client.OcpClient()
    src_vm = config.VMS_LIST[0]
    dst_vm = config.VMS_LIST[1]

    @pytest.mark.parametrize(
        "ip",
        [
            pytest.param("pod_ip"),
            pytest.param("ovs_ip"),
            pytest.param("bond_ip", marks=(pytest.mark.skipif(not config.BOND_SUPPORT_ENV, reason="No BOND support"))),
            pytest.param("non_vlan_ip")
        ],
        ids=[
            "Connectivity_between_VM_and_VM_over_POD_network",
            "Connectivity_between_VM_and_VM_over_Multus_with_OVS_network",
            "Connectivity_between_VM_and_VM_over_Multus_with_OVS_on_BOND_network",
            "Negative:_No_connectivity_from_non_VLAN_to_VLAN"
        ]
    )
    def test_connectivity(self, ip):
        """
        Check connectivity
        """
        _id = utils.get_test_parametrize_ids(item=self.test_connectivity.pytestmark, params=ip)
        LOGGER.info(_id)
        positive = ip != "non_vlan_ip"
        dst_ip = config.VMS.get(self.dst_vm).get(ip) if positive else config.OVS_NODES_IPS[0]
        src_vm_console = console.Console(vm=self.src_vm).fedora()
        assert src_vm_console
        src_vm_console.sendline("ping -w 3 {ip}".format(ip=dst_ip))
        src_vm_console.sendline("echo $?")
        src_vm_console.expect("0" if positive else "1")
        src_vm_console.sendline("exit")
        src_vm_console.send("\n\n")
        src_vm_console.expect("login:")
        src_vm_console.close()


class TestGuestPerformance(object):
    """
    In-guest performance bandwidth passthrough
    """
    server_vm = config.VMS_LIST[0]
    client_vm = config.VMS_LIST[1]

    def test_guest_performance(self):
        """
        In-guest performance bandwidth passthrough
        """
        server_vm = config.VMS_LIST[0]
        client_vm = config.VMS_LIST[1]
        server_ip = config.VMS.get(self.server_vm).get("ovs_ip")
        server_vm_console = console.Console(vm=server_vm).fedora()
        client_vm_console = console.Console(vm=client_vm).fedora()
        client_vm_console.logfile = sys.stdout

        server_vm_console.sendline("iperf3 -sB {server_ip}".format(server_ip=server_ip))
        client_vm_console.sendline("iperf3 -c {server_ip} -t 5".format(server_ip=server_ip))
        client_vm_console.expect("iperf Done.")
        before_out = client_vm_console.before
        LOGGER.info(before_out)
