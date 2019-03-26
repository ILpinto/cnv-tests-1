# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV network tests
"""


# def pytest_namespace():
#     return {
#         'active_node_nics': {},
#         'nodes_network_info': {},
#         'real_nics_env': False,
#         'bond_support_env': False
#     }


def pytest_configure():
    import pytest
    pytest.active_node_nics = {}
    pytest.nodes_network_info = {}
    pytest.real_nics_env = False
    pytest.bond_support_env = False
