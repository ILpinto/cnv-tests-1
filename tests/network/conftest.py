# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV network tests
"""

import pytest
from utilities import client
from tests.network import config


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    api = client.OcpClient()

    def fin():
        """
        Remove test namespaces
        """
        assert api.delete_namespace(name=config.NETWORK_NS, wait=True)
    request.addfinalizer(fin)

    assert api.create_namespace(name=config.NETWORK_NS, wait=True, switch=True)
