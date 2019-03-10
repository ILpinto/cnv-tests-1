import yaml
import logging
import urllib3
from kubernetes import config as kube_config
from openshift.dynamic import DynamicClient
from openshift.dynamic.exceptions import NotFoundError

from . import utils
from autologs.autologs import generate_logs

urllib3.disable_warnings()
LOGGER = logging.getLogger(__name__)
TIMEOUT = 120
SLEEP = 1


class OcpClient(object):
    def __init__(self):
        urllib3.disable_warnings()
        try:
            self.dyn_client = DynamicClient(kube_config.new_client_from_config())
        except (kube_config.ConfigException, urllib3.exceptions.MaxRetryError):
            LOGGER.error('You need to be login to cluster')
            raise

        self.vmi = 'VirtualMachineInstance'
        self.vm = 'VirtualMachine'
        self.kubvirt_v1alpha3 = 'kubevirt.io/v1alpha3'
        self.pod = "Pod"
        self.node = 'Node'
        self.apiv1 = 'v1'
        self.namespace = 'Namespace'

    def get_resource(self, name, api_version, kind, **kwargs):
        """
        Get resource

        Args:
            name (str): Resource name.
            api_version (str): API version of the resource.
            kind (str): The kind on the resource.

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
            dict: Resource dict.
        """
        resources = self.get_resources(api_version=api_version, kind=kind, **kwargs)
        res = [i for i in resources if i.get('metadata', {}).get('name') == name]
        return res[0] if res else {}

    def get_resources(self, api_version, kind, **kwargs):
        """
        Get resources

        Args:
            api_version (str): API version of the resource.
            kind (str): The kind on the resource.

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
            list: Resources.
        """
        return self.dyn_client.resources.get(
            api_version=api_version, kind=kind
        ).get(**kwargs).items

    @generate_logs()
    def wait_for_resource(self, name, api_version, kind, timeout=TIMEOUT, sleep=SLEEP, **kwargs):
        """
        Wait for resource

        Args:
            name (str): Resource name.
            api_version (str): API version of the resource.
            kind (str): The kind on the resource.
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
            bool: True if resource exists, False if timeout reached.
        """
        sample = utils.TimeoutSampler(
            timeout=timeout, sleep=sleep, func=lambda: bool(self.get_resource(
                name=name, api_version=api_version, kind=kind, **kwargs
            ))
        )
        return sample.wait_for_func_status(result=True)

    @generate_logs()
    def wait_for_resource_to_be_gone(self, name, api_version, kind, timeout=TIMEOUT, sleep=SLEEP, **kwargs):
        """
        Wait until resource is not exists

        Args:
            name (str): Resource name.
            api_version (str): API version of the resource.
            kind (str): The kind on the resource.
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
            bool: True if resource exists, False if timeout reached.
        """
        sample = utils.TimeoutSampler(
            timeout=timeout, sleep=sleep, func=lambda: bool(self.get_resource(
                name=name, api_version=api_version, kind=kind, **kwargs
            ))
        )
        return sample.wait_for_func_status(result=False)

    @generate_logs()
    def wait_for_resource_status(self, name, api_version, kind, status, timeout=TIMEOUT, sleep=SLEEP, **kwargs):
        """
        Wait for resource to be in desire status

        Args:
            name (str): Resource name.
            api_version (str): API version of the resource.
            kind (str): The kind on the resource.
            status (str): Expected status.
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
        sampler = utils.TimeoutSampler(
            timeout=timeout, sleep=sleep, func=lambda: self.get_resource(
                name=name, api_version=api_version, kind=kind, **kwargs
            ).status.phase == status
        )
        return sampler.wait_for_func_status(result=True)

    @generate_logs()
    def create_resource(self, yaml_file=None, resource_dict=None, namespace=None, wait=False):
        """
        Create resource from given yaml file or from dict

        Args:
            yaml_file (str): Path to yaml file.
            resource_dict (dict): Dict to create resource from.
            namespace (str): Namespace name for the object
            wait (bool) : True to wait for resource status.

        Raises:
            AssertionError: If missing parameter.

        Returns:
            bool: True if create succeeded, False otherwise.
        """
        assert (yaml_file or resource_dict), "Yaml file or resource dict is needed"

        if not resource_dict:
            with open(yaml_file, 'r') as stream:
                resource_dict = yaml.load(stream)

        namespace = resource_dict.get('metadata', {}).get('namespace', namespace)
        resource_name = resource_dict.get('metadata', {}).get('name')
        api_ver = resource_dict.get('apiVersion')
        kind = resource_dict.get('kind')
        obj = self.dyn_client.resources.get(api_version=api_ver, kind=kind)
        obj.create(body=resource_dict, namespace=namespace)
        if wait:
            return self.wait_for_resource(name=resource_name, api_version=api_ver, kind=kind)
        return True

    def delete_resource(self, name, namespace, api_version, kind, wait=False):
        """
        Delete resource

        Args:
            name (str): Pod name.
            namespace (str): Namespace name.
            api_version (str): API version.
            kind (str): Resource kind.
            wait (bool): True to wait for pod to be deleted.

        Returns:

        """
        obj = self.dyn_client.resources.get(api_version=api_version, kind=kind)
        try:
            obj.delete(name=name, namespace=namespace)
        except NotFoundError:
            return False

        if wait:

            return self.wait_for_resource_to_be_gone(name=name, api_version=api_version, kind=kind)
        return True

    @generate_logs()
    def delete_resource_from_yaml(self, yaml_file, wait=False):
        """
        Delete resource from given yaml file or from dict

        Args:
            yaml_file (str): Path to yaml file.
            wait (bool) : True to wait for resource status.

        Raises:
            AssertionError: If missing parameter

        Returns:
            bool: True if delete succeeded, False otherwise.
        """
        with open(yaml_file, 'r') as stream:
            resource_dict = yaml.load(stream)

        namespace = resource_dict.get('metadata').get('namespace')
        resource_name = resource_dict.get('metadata').get('name')
        api_ver = resource_dict.get('apiVersion')
        kind = resource_dict.get('kind')
        obj = self.dyn_client.resources.get(api_version=api_ver, kind=kind)
        try:
            obj.delete(name=resource_name, namespace=namespace)
        except NotFoundError:
            return False

        if wait:
            return self.wait_for_resource_to_be_gone(name=resource_name, api_version=api_ver, kind=kind)
        return True

    @generate_logs()
    def get_namespace(self, namespace):
        """
        Get namespace

        Args:
            namespace (str): Namespace name.

        Returns:
            dict: Namespace dict.
        """
        return self.get_resource(name=namespace, api_version=self.apiv1, kind=self.namespace)

    @generate_logs()
    def create_namespace(self, name, wait=False, switch=False):
        """
        Create a namespace

        Args:
            name (str): Namespace name.
            wait (bool) : True to wait for resource status.
            switch (bool): Switch to created namespace (project)

        Returns:
            bool: True if create succeeded, False otherwise
        """
        body = {
            'apiVersion': self.apiv1,
            'kind': self.namespace,
            'metadata': {'name': name}
        }
        res = self.create_resource(resource_dict=body, wait=wait)
        if switch and res:
            return self.switch_project(name=name)
        return res

    @generate_logs()
    def delete_namespace(self, name, wait=False):
        """
        Delete namespace

        Args:
            name (str): Namespace name to delete.
            wait (bool) : True to wait for resource status.

        Returns:
            bool: True if delete succeeded, False otherwise
        """
        return self.delete_resource(
            name=name, namespace=name, api_version=self.apiv1, kind=self.namespace, wait=wait
        )

    @generate_logs()
    def get_nodes(self, label_selector=None):
        """
        Get nodes

        Args:
            label_selector (str): Node label to filter with

        Returns:
            list: List of nodes
        """
        return self.get_resources(api_version=self.apiv1, kind=self.node, label_selector=label_selector)

    @generate_logs()
    def get_pods(self, label_selector=None):
        """
        Get pods

        Args:
            label_selector (str): Pod label to filter with

        Returns:
            list: List of pods
        """
        return self.get_resources(api_version=self.apiv1, kind=self.pod, label_selector=label_selector)

    @generate_logs()
    def get_vmis(self):
        """
        Return List with all the VMI objects

        Returns:
            list: List of VMIs
        """
        return self.get_resources(api_version=self.kubvirt_v1alpha3, kind=self.vmi)

    @generate_logs()
    def get_vmi(self, name):
        """
        Get VMI

        Returns:
            dict: VMI
        """
        return self.get_resource(name=name, api_version=self.kubvirt_v1alpha3, kind=self.vmi)

    @generate_logs()
    def delete_pod(self, name, namespace, wait=False):
        """
        Delete Pod

        Args:
            name (str): Pod name.
            namespace (str): Namespace name.
            wait (bool): True to wait for pod to be deleted.

        Returns:
            bool: True if delete succeeded, False otherwise.
        """
        return self.delete_resource(
            name=name, namespace=namespace, api_version=self.apiv1, kind=self.pod, wait=wait
        )

    @generate_logs()
    def switch_project(self, name):
        """
        Set working project

        Args:
            name (str): Project name

        Returns:
            bool: True if switch succeeded, False otherwise
        """
        return utils.run_command(command="oc project {name}".format(name=name))[0]

    @generate_logs()
    def delete_vm(self, name, namespace, wait=False):
        """
        Delete VM

        Args:
            name (str): VM name.
            namespace (str): Namespace name.
            wait (bool): True to wait for pod to be deleted.

        Returns:
            bool: True if delete succeeded, False otherwise.
        """
        return self.delete_resource(
            name=name, namespace=namespace, api_version=self.kubvirt_v1alpha3, kind=self.vm,
            wait=wait
        )

    @generate_logs()
    def wait_for_vmi_status(self, name, status):
        """
        Wait for VM status

        Args:
            name (str): VMI name
            status (str): Desire status.

        Returns:
            bool: True if resource in desire status, False if timeout reached.
        """
        return self.wait_for_resource_status(
            name=name, api_version=self.kubvirt_v1alpha3, kind=self.vmi, status=status
        )

    @generate_logs()
    def wait_for_pod_status(self, name, status):
        """
        Wait for Pod status

        Args:
            name (str): Pod name
            status (str): Desire status.

        Returns:
            bool: True if resource in desire status, False if timeout reached.
        """
        return self.wait_for_resource_status(
            name=name, api_version=self.apiv1, kind=self.pod, status=status
        )
