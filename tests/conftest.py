# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV tests
"""

import os

import pytest

from resources.namespace import NameSpace
from utilities import types

from . import config


def pytest_collection_modifyitems(session, config, items):
    """
    Add polarion test case it from tests to junit xml
    """
    for item in items:
        for marker in item.iter_markers(name='polarion'):
            test_id = marker.args[0]
            item.user_properties.append(('polarion-testcase-id', test_id))

        for marker in item.iter_markers(name='bugzilla'):
            test_id = marker.args[0]
            item.user_properties.append(('bugzilla', test_id))

        for marker in item.iter_markers(name='jira'):
            test_id = marker.args[0]
            item.user_properties.append(('jira', test_id))


def pytest_runtest_makereport(item, call):
    """
    incremental tests implementation
    """
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    """
    Use incremental
    """
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" % previousfailed.name)


@pytest.fixture(scope="session", autouse=True)
def junitxml_polarion(request):
    """
    Add polarion needed attributes to junit xml

    export as os environment:
        POLARION_CUSTOM_PLANNEDIN
        POLARION_TESTRUN_ID
    """
    if request.config.pluginmanager.hasplugin('junitxml'):
        my_junit = getattr(request.config, "_xml", None)
        if my_junit:
            my_junit.add_global_property('polarion-custom-isautomated', 'True')
            my_junit.add_global_property('polarion-testrun-status-id', 'inprogress')
            my_junit.add_global_property('polarion-custom-plannedin', os.getenv('POLARION_CUSTOM_PLANNEDIN'))
            my_junit.add_global_property('polarion-user-id', 'cnvqe')
            my_junit.add_global_property('polarion-project-id', 'CNV')
            my_junit.add_global_property('polarion-response-myproduct', 'cnv-test-run')
            my_junit.add_global_property('polarion-testrun-id', os.getenv('POLARION_TESTRUN_ID'))


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    namespaces = (config.TEST_NS, config.TEST_NS_ALTERNATIVE)

    def fin():
        """
        Remove test namespaces
        """
        for namespace in namespaces:
            ns = NameSpace(name=namespace)
            ns.delete(wait=True)
    request.addfinalizer(fin)

    for namespace in namespaces:
        ns = NameSpace(name=namespace)
        ns.create(wait=True)
        ns.wait_for_status(status=types.ACTIVE)
