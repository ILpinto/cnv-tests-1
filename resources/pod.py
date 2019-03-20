from .resource import Resource
from utilities import types
from utilities import utils


class Pod(Resource):
    """
    NameSpace object, inherited from Resource.
    """
    def __init__(self, name=None, namespace=None):
        super(Pod, self).__init__()
        self.name = name
        self.namespace = namespace
        self.api_version = types.API_VERSION_V1
        self.kind = types.POD

    def containers(self):
        """
        Get Pod containers

        Returns:
            list: List of Pod containers
        """
        return self.get().spec.containers

    def run_command(self, command, container):
        """
        Run command on pod.

        Args:
            command (str): Command to run.
            container (str): Container name if pod has more then one.

        Returns:
            tuple: True, out if command succeeded, False, err otherwise.
        """
        cmd = f"oc exec -i {self.name}"
        if self.namespace:
            cmd += f" -n {self.namespace}"

        if container:
            cmd += f" -c {container}"

        cmd += f" -- {command}"
        return utils.run_command(command=cmd)

    def node(self):
        """
        Get the node name where the Pod is running

        Returns:
            str: Node name
        """
        return self.get().spec.nodeName
