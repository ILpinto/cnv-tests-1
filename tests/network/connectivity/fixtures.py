import logging

import pytest
from lib import client, utils
from . import config

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope='module', autouse=True)
def prepare_env(request):
    api = client.OcpClient()
    nodes_network_info = {}
    node_nics = []
    bond_name = config.BOND_NAME
    bond_bridge = config.BOND_BRIDGE
    bridge_name = config.BRIDGE_NAME
    vxlan_port = config.OVS_NO_VLAN_PORT
    vms = config.VMS_LIST

    def fin():
        """
        Remove test namespaces
        """
        utils.run_command(command=config.SVC_DELETE_CMD)
        for yaml_ in (config.PRIVILEGED_POD_YAML, config.OVS_VLAN_YAML, config.OVS_BOND_YAML):
            api.delete_resource_from_yaml(yaml_file=yaml_, wait=True)

        privileged_pods = api.get_pods(label_selector="app=privileged-test-pod")
        # Wait until privileged_pod deleted
        for pod in privileged_pods:
            pod_name = pod.metadata.name
            pod_container = pod.spec.containers[0].name
            utils.run_command_on_pod(
                command=config.OVS_VSCTL_DEL_BRIDGE_VXLAN, pod=pod_name, container=pod_container
            )
            if config.BOND_SUPPORT_ENV:
                utils.run_command_on_pod(
                    command=config.OVS_VSCTL_DEL_BRIDGE_BOND_VXLAN, pod=pod_name, container=pod_container
                )

            api.delete_pod(name=pod_name, namespace=pod.metadata.namespace, wait=True)

        for vm in vms:
            api.delete_vm(name=vm, namespace=config.NETWORK_NS, wait=True)

    request.addfinalizer(fin)

    compute_nodes = api.get_nodes(label_selector="node-role.kubernetes.io/compute=true")
    assert utils.run_command(command=config.SVC_CMD)[0]
    assert utils.run_command(command=config.ADM_CMD)[0]
    api.create_resource(yaml_file=config.PRIVILEGED_POD_YAML)
    privileged_pods = api.get_pods(label_selector="app=privileged-test-pod")
    assert len(compute_nodes) == len(privileged_pods)
    api.create_resource(yaml_file=config.OVS_VLAN_YAML)
    api.create_resource(yaml_file=config.OVS_BOND_YAML)
    for node in compute_nodes:
        for addr in node.status.addresses:
            if addr.type == "InternalIP":
                nodes_network_info[node.metadata.name] = addr.address
                break

    for idx, pod in enumerate(privileged_pods):
        pod_name = pod.metadata.name
        node_name = pod.spec.nodeName
        pod_container = pod.spec.containers[0].name
        assert api.wait_for_pod_status(name=pod_name, status="Running")
        node_nics = utils.run_command_on_pod(
            command=config.GET_NICS_CMD, pod=pod_name, container=pod_container
        )[1]
        node_nics = node_nics.splitlines()
        config.BOND_SUPPORT_ENV = len(node_nics) > 3
        assert utils.run_command_on_pod(
            command=config.OVS_VSCTL_ADD_BR.format(bridge=bridge_name),
            pod=pod_name, container=pod_container
        )[0]
        for name, ip in nodes_network_info.items():
            if name != node_name:
                assert utils.run_command_on_pod(
                    command=config.OVS_VSCTL_ADD_VXLAN.format(bridge=bridge_name, ip=ip),
                    pod=pod_name, container=pod_container
                )[0]
                break

        assert utils.run_command_on_pod(
            command=config.OVS_VSCTL_ADD_PORT_VXLAN.format(
                bridge=config.BRIDGE_NAME, port_1=vxlan_port, port_2=vxlan_port
            ), pod=pod_name, container=pod_container
        )[0]
        assert utils.run_command_on_pod(
            command=config.IP_ADDR_ADD.format(ip=config.OVS_NODES_IPS[idx], dev=vxlan_port),
            pod=pod_name, container=pod_container
        )[0]

    if config.BOND_SUPPORT_ENV:
        bond_commands = [
            config.IP_LINK_ADD_BOND,
            config.IP_LINK_SET_BOND_PARAMS,
        ]

        for pod in privileged_pods:
            pod_name = pod.metadata.name
            pod_container = pod.spec.containers[0].name
            for cmd in bond_commands:
                assert utils.run_command_on_pod(
                    command=cmd, pod=pod_name, container=pod_container
                )[0]
            for nic in node_nics[2:4]:
                assert utils.run_command_on_pod(
                    command=config.IP_LINK_INTERFACE_DOWN.format(interface=nic),
                    pod=pod_name, container=pod_container
                )[0]
                assert utils.run_command_on_pod(
                    command=config.IP_LINK_SET_INTERFACE_MASTER.format(interface=nic, bond=bond_name),
                    pod=pod_name, container=pod_container
                )[0]
                assert utils.run_command_on_pod(
                    command=config.IP_LINK_INTERFACE_UP.format(interface=nic),
                    pod=pod_name, container=pod_container
                )[0]
            assert utils.run_command_on_pod(
                command=config.IP_LINK_INTERFACE_UP.format(interface=bond_name),
                pod=pod_name, container=pod_container
            )[0]
            res, out = utils.run_command_on_pod(
                command=config.IP_LINK_SHOW.format(interface=bond_name),
                pod=pod_name, container=pod_container
            )
            assert res
            assert "state UP" not in out
            assert utils.run_command_on_pod(
                command=config.OVS_VSCTL_ADD_BR.format(bridge=bond_bridge),
                pod=pod_name, container=pod_container
            )[0]
            assert utils.run_command_on_pod(
                command=config.OVS_VSCTL_ADD_PORT.format(bridge=bond_bridge, interface=bond_name),
                pod=pod_name, container=pod_container
            )[0]

    for vm in vms:
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
        if config.BOND_SUPPORT_ENV:
            interfaces = spec.get('domain').get('devices').get('interfaces')
            networks = spec.get('networks')
            bond_bridge_interface = {'bridge': {}, 'name': 'ovs-net-bond'}
            bond_bridge_network = {'multus': {'networkName': 'ovs-net-bond'}, 'name': 'ovs-net-bond'}
            interfaces.append(bond_bridge_interface)
            networks.append(bond_bridge_network)
            cloud_init_user_data += (
                "- nmcli con add type ethernet con-name eth1 ifname eth2\n"
                "- nmcli con mod eth2 ipv4.addresses {ip}/24 ipv4.method manual\n".format(
                    ip=config.VMS.get(vm).get("bond_ip")
                )
            )
            spec['domain']['devices']['interfaces'] = interfaces
            spec['networks'] = networks

        cloud_init_data['cloudInitNoCloud']['userData'] = cloud_init_user_data
        volumes.append(cloud_init_data)
        spec['volumes'] = volumes
        json_out['spec']['template']['spec'] = spec
        assert api.create_resource(resource_dict=json_out, namespace=config.NETWORK_NS)

    for vmi in vms:
        assert api.wait_for_vmi_status(name=vmi, status="Running")
        wait_for_vm_interfaces(api=api, vmi=vmi)
        vmi_data = api.get_vmi(name=vmi)
        ifcs = vmi_data.get('status', {}).get('interfaces', [])
        active_ifcs = [i.get('ipAddress') for i in ifcs if i.get('interfaceName') == "eth0"]
        config.VMS[vmi]["pod_ip"] = active_ifcs[0].split("/")[0]


@utils.generate_logs()
def wait_for_vm_interfaces(api, vmi):
    """
    Wait until guest agent to report VMI interfaces.

    Args:
        api (DynamicClient): OCP lib instance.
        vmi (str): VMI name.

    Returns:
        bool: If agent report VMI interfaces.

    Raises:
        TimeoutExpiredError: After timeout reached.
    """
    sampler = utils.TimeoutSampler(timeout=420, sleep=1, func=api.get_vmi, name=vmi)
    for sample in sampler:
        ifcs = sample.get('status', {}).get('interfaces', [])
        active_ifcs = [i for i in ifcs if i.get('ipAddress') and i.get('interfaceName')]
        if len(active_ifcs) == len(ifcs):
            return True
