from tests.network.config import *  # noqa: F403

#  GENERAL
IP_LINK_SHOW_BETH_CMD = 'bash -c "ip -o link show type veth | wc -l"'

#  VMS
VMS = {
    "vm-fedora-1": {
        "pod_ip": None,
        "ovs_ip": "192.168.0.1",
        "bond_ip": "192.168.1.1"
    },
    "vm-fedora-2": {
        "pod_ip": None,
        "ovs_ip": "192.168.0.2",
        "bond_ip": "192.168.1.2"
    }
}
VMS_LIST = list(VMS.keys())
VM_YAML_TEMPLATE = "tests/manifests/network/vm-template-fedora-multus.yaml"

#  NODES
OVS_NODES_IPS = ["192.168.0.3", "192.168.0.4"]
GET_NICS_CMD = "bash -c 'ls -l /sys/class/net/ | grep -v virtual | grep net | rev | cut -d '/' -f 1 | rev'"

#  OVS
OVS_DB = "--db unix:/host/run/openvswitch/db.sock"
OVS_CMD = f"ovs-vsctl {OVS_DB}"
OVS_VLAN_YAML_VXLAN = "tests/manifests/network/ovs-vlan-net-vxlan.yml"
OVS_VLAN_YAML = "tests/manifests/network/ovs-vlan-net.yml"
OVS_NO_VLAN_PORT = f"{OVS_CMD} ovs_novlan_port"
OVS_VSCTL_ADD_BR = f"{OVS_CMD} add-br"
OVS_VSCTL_ADD_PORT = f"{OVS_CMD} add-port"
OVS_VSCTL_DEL_BR = f"{OVS_CMD} del-br"

#  VXLAN
BRIDGE_NAME_VXLAN = "br1_for_vxlan"

# BOND
BOND_SUPPORT_ENV = None
OVS_BOND_YAML = "tests/manifests/network/ovs-net-bond.yml"
BOND_NAME = "bond1"
BOND_BRIDGE = "br1_for_bond"
IP_LINK_INTERFACE_DOWN = "ip link set {interface} down"
IP_LINK_INTERFACE_UP = "ip link set {interface} up"

# REAL NICS
REAL_NICS_ENV = None
CHECK_NIC_DRIVER_CMD = "bash -c 'basename $(readlink -f /sys/class/net/{nic}/device/driver/module/)'"
BRIDGE_NAME_REAL_NICS = "br1_real_nics"

ALL_BRIDGES = [BRIDGE_NAME_REAL_NICS, BRIDGE_NAME_VXLAN, BOND_BRIDGE]
