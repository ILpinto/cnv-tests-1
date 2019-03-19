import os
import yaml
import logging
import urllib3
from kubernetes import config as kube_config
from openshift.dynamic import DynamicClient
from openshift.dynamic.exceptions import NotFoundError
from autologs.autologs import generate_logs
from utilities import utils

LOGGER = logging.getLogger(__name__)
TIMEOUT = 120
SLEEP = 1


class Resource(object):
    def __init__(self):
        urllib3.disable_warnings()
        try:
            kubeconfig = os.getenv('KUBECONFIG')
            self.client = DynamicClient(kube_config.new_client_from_config(config_file=kubeconfig))
        except (kube_config.ConfigException, urllib3.exceptions.MaxRetryError):
            LOGGER.error('You need to be login to cluster or have $KUBECONFIG env configured')
            raise
        
        self.kind = None
        self.namespace = None
        self.api_version = None
        self.name = None

    def get(self, **kwargs):
        """
        Get resource

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
            namespace

        Returns:
            dict: Resource dict.
        """
        kwargs['namespace'] = self.namespace
        resources = self.list(api_version=self.api_version, kind=self.kind, **kwargs)
        res = [i for i in resources if i.get('metadata', {}).get('name') == self.name]
        return res[0] if res else {}

    def list(self, **kwargs):
        """
        Get resources list

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
            namespace

        Returns:
            list: Resources.
        """
        return self.client.resources.get(api_version=self.api_version, kind=self.kind).get(**kwargs).items

    @generate_logs()
    def wait(self, timeout=TIMEOUT, sleep=SLEEP):
        """
        Wait for resource

        Args:
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.

        Returns:
            bool: True if resource exists, False if timeout reached.
        """
        sample = utils.TimeoutSampler(timeout=timeout, sleep=sleep, func=lambda: bool(self.get()))
        return sample.wait_for_func_status(result=True)

    @generate_logs()
    def wait_until_gone(self, timeout=TIMEOUT, sleep=SLEEP):
        """
        Wait until resource is not exists

        Args:
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.

        Returns:
            bool: True if resource exists, False if timeout reached.
        """
        sample = utils.TimeoutSampler(timeout=timeout, sleep=sleep, func=lambda: bool(self.get()))
        return sample.wait_for_func_status(result=False)

    @generate_logs()
    def wait_for_status(self, status, timeout=TIMEOUT, sleep=SLEEP):
        """
        Wait for resource to be in status

        Args:
            status (str): Expected status.
            timeout (int): Time to wait for the resource.
            sleep (int): Time to sleep between retries.

        Returns:
            bool: True if resource in desire status, False if timeout reached.
        """
        sampler = utils.TimeoutSampler(timeout=timeout, sleep=sleep, func=lambda: self.status() == status)
        return sampler.wait_for_func_status(result=True)

    @generate_logs()
    def create(self, yaml_file=None, resource_dict=None, wait=False):
        """
        Create resource from given yaml file or from dict

        Args:
            yaml_file (str): Path to yaml file.
            resource_dict (dict): Dict to create resource from.
            wait (bool) : True to wait for resource status.

        Raises:
            AssertionError: If missing parameter.

        Returns:
            bool: True if create succeeded, False otherwise.
        """
        # assert (yaml_file or resource_dict), "Yaml file or resource dict is needed"
        
        if yaml_file:
            with open(yaml_file, 'r') as stream:
                resource_dict = yaml.full_load(stream)
        if not resource_dict:
            resource_dict = {
                'apiVersion': self.api_version,
                'kind': self.kind,
                'metadata': {'name': self.namespace}
            }

        resource_list = self.client.resources.get(api_version=self.api_version, kind=self.kind)
        resource_list.create(body=resource_dict, namespace=self.namespace)
        if wait:
            return self.wait(name=self.name, api_version=self.api_version, kind=self.kind)
        return True

    def delete(self, wait=False):
        """
        Delete resource

        Args:
            wait (bool): True to wait for pod to be deleted.

        Returns:
            True if delete succeeded, False otherwise.

        """
        resource_list = self.client.resources.get(api_version=self.api_version, kind=self.kind)
        try:
            resource_list.delete(name=self.name, namespace=self.namespace)
        except NotFoundError:
            return False

        if wait:
            return self.wait_until_gone(name=self.name, api_version=self.api_version, kind=self.kind)
        return True

    def status(self):
        """
        Return resource status
        Status: Running,Scheduling, Pending, Unknown, CrashLoopBackOff

        Returns:
           list: List with vmi with the
        """
        return self.get().status.phase
