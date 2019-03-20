# -*- coding: utf-8 -*-

import logging
from tests import config
from .resource import Resource, SLEEP, TIMEOUT
from utilities import utils, types
from autologs.autologs import generate_logs

LOGGER = logging.getLogger(__name__)


class VirtualMachine(Resource):
    """
    Virtual Machine object, inherited from Resource.
    Implements actions start / stop / status / wait for VM status / is running
    """
    
    def __init__(self, name, namespace=None):
        super(VirtualMachine, self).__init__()
        self.name = name
        self.namespace = namespace
        self.api_version = types.CNV_API_VERSION
        self.kind = types.VM
        self.cmd = f"{config.VIRTCTL_CMD}"
        if self.namespace:
            self.cmd += f" -n {self.namespace}"
    
    @generate_logs()
    def start(self, timeout=TIMEOUT, sleep=SLEEP, wait=False):
        """
        Start VM with virtctl
        Args:
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.
            wait (bool): If True wait else Not

        Returns:
            True if VM started, else False

        """
        cmd_start = f"{self.cmd} start {self.name}"
        res = utils.run_command(command=cmd_start)[0]
        if wait and res:
            return self.wait_for_status(sleep=sleep, timeout=timeout, status=True)
        return res
    
    @generate_logs()
    def stop(self, timeout=TIMEOUT, sleep=SLEEP, wait=False):
        """
        Stop VM with virtctl
        Args:
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.
            wait (bool): If True wait else Not

        Returns:
            bool: True if VM stopped, else False

        """
        cmd_stop = f"{self.cmd} stop {self.name}"
        res = utils.run_command(command=cmd_stop)[0]
        if wait and res:
            return self.wait_for_status(sleep=sleep, timeout=timeout, status=False)
        return res
            
    @generate_logs()
    def wait_for_status(self, status, timeout=TIMEOUT, sleep=SLEEP, **kwargs):
        """
        Wait for resource to be in status

        Args:
            status (bool): Expected status(True vm is running, False vm is not running).
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.

        Keyword Args:
            pretty
            _continue
            include_uninitialized
            field_selector
            label_selector
            limit
            resource_version
            timeout_seconds
            watch
            async_req

        Returns:
            bool: True if resource in desire status, False if timeout reached.
        """
        sampler = utils.TimeoutSampler(timeout=timeout, sleep=sleep, func=lambda: self.get().spec.running == status)
        return sampler.wait_for_func_status(result=True)

    def node(self):
        """
        Get the node name where the VM is running

        Returns:
            str: Node name
        """
        return self.get().status.nodeName
