# -*- coding: utf-8 -*-

import logging

from utilities import types

from .resource import Resource

LOGGER = logging.getLogger(__name__)


class VirtualMachineInstance(Resource):
    """
    Virtual Machine object, inherited from Resource.
    Implements actions start / stop / status / wait for VM status / is running
    """
    def __init__(self, name, namespace=None):
        super(VirtualMachineInstance, self).__init__()
        self.name = name
        self.namespace = namespace
        self.api_version = types.CNV_API_VERSION
        self.kind = types.VMI
