# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV VIRT tests
"""

import pytest
from tests.virt import config
from utilities import types
from resources.namespace import NameSpace


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    def fin():
        """
        Remove test namespaces
        """
        ns = NameSpace(name=config.VIRT_NS)
        ns.delete(wait=True)
    request.addfinalizer(fin)

    ns = NameSpace(name=config.VIRT_NS)
    ns.create(wait=True)
    ns.wait_for_status(status=types.ACTIVE)
    ns.work_on()
