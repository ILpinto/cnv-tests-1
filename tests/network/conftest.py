# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV network tests
"""

import pytest
from tests.network import config

from resources.namespace import NameSpace
from utilities import types


@pytest.fixture(scope="session", autouse=True)
def network_init(request):
    """
    Create network test namespaces
    """
    def fin():
        """
        Remove network test namespaces
        """
        ns = NameSpace(name=config.NETWORK_NS)
        ns.delete(wait=True)
    request.addfinalizer(fin)

    ns = NameSpace(name=config.NETWORK_NS)
    ns.create(wait=True)
    ns.wait_for_status(status=types.ACTIVE)
    ns.work_on()
