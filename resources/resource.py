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
    def __init__(self, name=None, api_version=None, kind=None, namespace=None):
        urllib3.disable_warnings()
        try:
            kubeconfig = os.getenv('KUBECONFIG')
            self.client = DynamicClient(kube_config.new_client_from_config(config_file=kubeconfig))
        except (kube_config.ConfigException, urllib3.exceptions.MaxRetryError):
            LOGGER.error('You need to be login to cluster or have $KUBECONFIG env configured')
            raise

        self.kind = kind
        self.namespace = namespace
        self.api_version = api_version
        self.name = name

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

    @generate_logs()
    def list(self, **kwargs):
        """
        Get resources list

        Keyword Args:
            get_names (bool): Return objects names only
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
        list_items = self.client.resources.get(api_version=self.api_version, kind=self.kind).get(**kwargs).items
        if kwargs.pop('get_names', None):
            return [i.get('metadata', {}).get('name') for i in list_items]
        return list_items

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

        Returns:
            bool: True if create succeeded, False otherwise.
        """
        if yaml_file:
            with open(yaml_file, 'r') as stream:
                data = yaml.full_load(stream)

            self._extract_data_from_yaml(yaml_data=data)
            res = utils.run_oc_command(command=f'create -f {yaml_file}', namespace=self.namespace)[0]
            if wait and res:
                return self.wait()
            return res

        if not resource_dict:
            resource_dict = {
                'apiVersion': self.api_version,
                'kind': self.kind,
                'metadata': {'name': self.namespace}
            }

        resource_list = self.client.resources.get(api_version=self.api_version, kind=self.kind)
        res = resource_list.create(body=resource_dict, namespace=self.namespace)
        if wait and res:
            return self.wait()
        return res

    @generate_logs()
    def delete(self, yaml_file=None, wait=False):
        """
        Delete resource

        Args:
            yaml_file (str): Path to yaml file to delete from yaml.
            wait (bool): True to wait for pod to be deleted.

        Returns:
            True if delete succeeded, False otherwise.
        """
        if yaml_file:
            with open(yaml_file, 'r') as stream:
                data = yaml.full_load(stream)

            self._extract_data_from_yaml(yaml_data=data)
            res = utils.run_oc_command(command=f'delete -f {yaml_file}', namespace=self.namespace)[0]
            if wait and res:
                return self.wait_until_gone()
            return res

        resource_list = self.client.resources.get(api_version=self.api_version, kind=self.kind)
        try:
            res = resource_list.delete(name=self.name, namespace=self.namespace)
            if wait and res:
                return self.wait_until_gone()
            return res
        except NotFoundError:
            return False

    @generate_logs()
    def status(self):
        """
        Get resource status

        Status: Running,Scheduling, Pending, Unknown, CrashLoopBackOff

        Returns:
           str: Status
        """
        return self.get().status.phase

    def _extract_data_from_yaml(self, yaml_data):
        """
        Extract data from yaml stream

        Args:
            yaml_data (dict): Dict from yaml file
        """
        self.namespace = yaml_data.get('metadata').get('namespace')
        self.name = yaml_data.get('metadata').get('name')
        self.api_version = yaml_data.get('apiVersion')
        self.kind = yaml_data.get('kind')
