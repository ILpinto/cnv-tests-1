import logging

import pytest
from utilities import client, utils, types
from resources.node import Node
from resources.virtual_machine import VirtualMachine
from resources.virtual_machine_instance import VirtualMachineInstance
from resources.pod import Pod
from resources.resource import Resource
from autologs.autologs import generate_logs
from . import config

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope='module', autouse=True)
def prepare_env(request):
    nodes_network_info = {}
    bond_name = config.BOND_NAME
    bond_bridge = config.BOND_BRIDGE
    bridge_name_vxlan = config.BRIDGE_NAME_VXLAN
    bridge_name_real_nics = config.BRIDGE_NAME_REAL_NICS
    vxlan_port = config.OVS_NO_VLAN_PORT
    vms = config.VMS_LIST
    active_node_nics = {}

    def fin():
        """
        Remove test namespaces
        """
        for pod in config.PRIVILEGED_PODS:
            pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
            pod_container = pod_object.containers()[0].name
            for bridge in config.ALL_BRIDGES:
                pod_object.run_command(command=config.OVS_VSCTL_DEL_BR.format(bridge=bridge), container=pod_container)

            if config.BOND_SUPPORT_ENV:
                pod_object.run_command(command=config.IP_LINK_DEL_BOND, container=pod_container)

        for vm in vms:
            vm_object = VirtualMachine(name=vm, namespace=config.NETWORK_NS)
            if vm_object.get():
                vm_object.delete(wait=True)

        utils.run_command(command=config.SVC_DELETE_CMD)
        for yaml_ in (config.PRIVILEGED_DAEMONSET_YAML, config.OVS_VLAN_YAML, config.OVS_BOND_YAML):
            Resource().delete(yaml_file=yaml_, wait=True)

    request.addfinalizer(fin)

    compute_nodes = Node().list(get_names=True, label_selector="node-role.kubernetes.io/compute=true")
    assert utils.run_command(command=config.SVC_CMD)[0]
    assert utils.run_command(command=config.ADM_CMD)[0]
    assert Resource().create(yaml_file=config.PRIVILEGED_DAEMONSET_YAML)
    wait_for_pods_to_match_compute_nodes_number(number_of_nodes=len(compute_nodes))
    config.PRIVILEGED_PODS = Pod().list(get_names=True, label_selector="app=privileged-test-pod")
    assert Resource().create(yaml_file=config.OVS_VLAN_YAML)
    assert Resource().create(yaml_file=config.OVS_BOND_YAML)
    for node in compute_nodes:
        node_obj = Node(name=node, namespace=config.NETWORK_NS)
        node_info = node_obj.get()
        for addr in node_info.status.addresses:
            if addr.type == "InternalIP":
                nodes_network_info[node] = addr.address
                break

    #  Check if we running with real NICs (not on VM)
    #  Check the number of the NICs on the node to ser BOND support
    for idx, pod in enumerate(config.PRIVILEGED_PODS):
        pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
        pod_container = pod_object.containers()[0].name
        active_node_nics[pod] = []
        assert pod_object.wait_for_status(status=types.RUNNING)
        err, nics = pod_object.run_command(command=config.GET_NICS_CMD, container=pod_container)
        assert err
        nics = nics.splitlines()
        err, default_gw = pod_object.run_command(command=config.GET_DEFAULT_GW_CMD, container=pod_container)
        assert err
        for nic in nics:
            err, nic_state = pod_object.run_command(
                command=config.GET_NIC_STATE_CMD.format(nic=nic), container=pod_container
            )
            assert err
            if nic_state.strip() == "up":
                if nic in [i for i in default_gw.splitlines() if 'default' in i][0]:
                    continue

                active_node_nics[pod].append(nic)

                err, driver = pod_object.run_command(
                    command=config.CHECK_NIC_DRIVER_CMD.format(nic=nic), container=pod_container
                )
                assert err
                config.REAL_NICS_ENV = driver.strip() != "virtio_net"

        config.BOND_SUPPORT_ENV = len(active_node_nics[pod]) > 3

    #  Configure bridges on the nodes
    for idx, pod in enumerate(config.PRIVILEGED_PODS):
        pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
        pod_name = pod
        node_name = pod_object.node()
        pod_container = pod_object.containers()[0].name
        if config.REAL_NICS_ENV:
            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_BR.format(bridge=bridge_name_real_nics), container=pod_container
            )[0]

            config.CREATED_BRIDGES.add(bridge_name_real_nics)
            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_PORT.format(
                    bridge=bridge_name_real_nics, interface=active_node_nics[pod_name][0]
                ), container=pod_container
            )[0]
        else:
            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_BR.format(bridge=bridge_name_vxlan), container=pod_container
            )[0]
            config.CREATED_BRIDGES.add(bridge_name_vxlan)
            for name, ip in nodes_network_info.items():
                if name != node_name:
                    assert pod_object.run_command(
                        command=config.OVS_VSCTL_ADD_VXLAN.format(bridge=bridge_name_vxlan, ip=ip),
                        container=pod_container
                    )[0]
                    break

            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_PORT_VXLAN.format(
                    bridge=config.BRIDGE_NAME_VXLAN, port_1=vxlan_port, port_2=vxlan_port
                ), container=pod_container
            )[0]

            assert pod_object.run_command(
                command=config.IP_ADDR_ADD.format(ip=config.OVS_NODES_IPS[idx], dev=vxlan_port),
                container=pod_container
            )[0]

    #  Configure bridge on BOND if env support BOND
    if config.BOND_SUPPORT_ENV:
        bond_commands = [config.IP_LINK_ADD_BOND, config.IP_LINK_SET_BOND_PARAMS]
        for pod in config.PRIVILEGED_PODS:
            pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
            pod_name = pod
            pod_container = pod_object.containers()[0].name
            for cmd in bond_commands:
                assert pod_object.run_command(command=cmd,container=pod_container)[0]

            for nic in active_node_nics[pod_name][1:3]:
                assert pod_object.run_command(
                    command=config.IP_LINK_INTERFACE_DOWN.format(interface=nic), container=pod_container
                )[0]

                assert pod_object.run_command(
                    command=config.IP_LINK_SET_INTERFACE_MASTER.format(interface=nic, bond=bond_name),
                    container=pod_container
                )[0]

                assert pod_object.run_command(
                    command=config.IP_LINK_INTERFACE_UP.format(interface=nic), container=pod_container
                )[0]

            assert pod_object.run_command(
                command=config.IP_LINK_INTERFACE_UP.format(interface=bond_name), container=pod_container
            )[0]

            res, out = pod_object.run_command(
                command=config.IP_LINK_SHOW.format(interface=bond_name), container=pod_container
            )

            assert res
            assert "state UP" in out

            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_BR.format(bridge=bond_bridge), container=pod_container
            )[0]

            config.CREATED_BRIDGES.add(bond_bridge)
            assert pod_object.run_command(
                command=config.OVS_VSCTL_ADD_PORT.format(bridge=bond_bridge, interface=bond_name),
                container=pod_container
            )[0]

    for vm in vms:
        vm_object = VirtualMachine(name=vm, namespace=config.NETWORK_NS)
        json_out = utils.get_json_from_template(
            file_=config.VM_YAML_TEMPLATE, NAME=vm, MULTUS_NETWORK="ovs-vlan-net"
        )
        spec = json_out.get('spec').get('template').get('spec')
        volumes = spec.get('volumes')
        cloud_init = [i for i in volumes if 'cloudInitNoCloud' in i][0]
        cloud_init_data = volumes.pop(volumes.index(cloud_init))
        cloud_init_user_data = cloud_init_data.get('cloudInitNoCloud').get('userData')
        cloud_init_user_data += (
            "\nruncmd:\n"
            "  - nmcli con add type ethernet con-name eth1 ifname eth1\n"
            "  - nmcli con mod eth1 ipv4.addresses {ip}/24 ipv4.method manual\n"
            "  - systemctl start qemu-guest-agent\n".format(ip=config.VMS.get(vm).get("ovs_ip"))
        )
        if not config.REAL_NICS_ENV:
            cloud_init_user_data += "  - ip link set mtu 1450 eth1\n"

        if config.BOND_SUPPORT_ENV:
            interfaces = spec.get('domain').get('devices').get('interfaces')
            networks = spec.get('networks')
            bond_bridge_interface = {'bridge': {}, 'name': 'ovs-net-bond'}
            bond_bridge_network = {'multus': {'networkName': 'ovs-net-bond'}, 'name': 'ovs-net-bond'}
            interfaces.append(bond_bridge_interface)
            networks.append(bond_bridge_network)
            cloud_init_user_data += (
                "  - nmcli con add type ethernet con-name eth1 ifname eth2\n"
                "  - nmcli con mod eth2 ipv4.addresses {ip}/24 ipv4.method manual\n".format(
                    ip=config.VMS.get(vm).get("bond_ip")
                )
            )
            spec['domain']['devices']['interfaces'] = interfaces
            spec['networks'] = networks

        cloud_init_data['cloudInitNoCloud']['userData'] = cloud_init_user_data
        volumes.append(cloud_init_data)
        spec['volumes'] = volumes
        json_out['spec']['template']['spec'] = spec
        assert vm_object.create(resource_dict=json_out, wait=True)

    for vmi in vms:
        vmi_object = VirtualMachineInstance(name=vmi, namespace=config.NETWORK_NS)
        assert vmi_object.wait_for_status(status=types.RUNNING)
        wait_for_vm_interfaces(vmi=vmi)
        vmi_data = VirtualMachineInstance.get()
        ifcs = vmi_data.get('status', {}).get('interfaces', [])
        active_ifcs = [i.get('ipAddress') for i in ifcs if i.get('interfaceName') == "eth0"]
        config.VMS[vmi]["pod_ip"] = active_ifcs[0].split("/")[0]


@generate_logs()
def wait_for_vm_interfaces(vmi):
    """
    Wait until guest agent report VMI interfaces.

    Args:
        vmi (VirtualMachineInstance): VMI object.

    Returns:
        bool: True if agent report VMI interfaces.

    Raises:
        TimeoutExpiredError: After timeout reached.
    """
    sampler = utils.TimeoutSampler(timeout=500, sleep=1, func=vmi.get(), vmi=vmi)
    for sample in sampler:
        ifcs = sample.get('status', {}).get('interfaces', [])
        active_ifcs = [i for i in ifcs if i.get('ipAddress') and i.get('interfaceName')]
        if len(active_ifcs) == len(ifcs):
            return True


@generate_logs()
def wait_for_pods_to_match_compute_nodes_number(number_of_nodes):
    """
    Wait for pods to be created from DaemonSet

    Args:
        number_of_nodes (int): Number of nodes to match for.

    Returns:
        bool: True if Pods created.

    Raises:
        TimeoutExpiredError: After timeout reached.

    """
    sampler = utils.TimeoutSampler(
        timeout=30, sleep=1, func=Pod().list, get_names=True, label_selector="app=privileged-test-pod"
    )
    for sample in sampler:
        if len(sample) == number_of_nodes:
            return True
