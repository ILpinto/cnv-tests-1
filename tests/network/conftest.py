# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV network tests
"""

import pytest
from tests.network import config
from utilities import types
from resources.namespace import NameSpace
from resources.pod import Pod


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    def fin():
        """
        Remove test namespaces
        """
        ns = NameSpace(name=config.NETWORK_NS)
        ns.delete(wait=True)
    request.addfinalizer(fin)

    ns = NameSpace(name=config.NETWORK_NS)
    ns.create(wait=True)
    ns.wait_for_status(status=types.ACTIVE)
    ns.work_on()
    pods = Pod().list(get_names=True)
    pods = [i for i in pods if i in "ovs-cni"]

    "oc exec -it ovs-cni-amd64-fzrrv -n kube-system -c ovs-cni-marker bash"