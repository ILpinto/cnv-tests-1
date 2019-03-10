# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV tests
"""

import pytest
from utilities import client
from . import config


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    namespaces = (config.TEST_NS, config.TEST_NS_ALTERNATIVE)
    api = client.OcpClient()

    def fin():
        """
        Remove test namespaces
        """
        for namespace in namespaces:
            api.delete_namespace(name=namespace, wait=True)
    request.addfinalizer(fin)

    for namespace in namespaces:
        api.create_namespace(namespace=namespace, wait=True)
