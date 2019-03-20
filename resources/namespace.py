from .resource import Resource
from utilities import types
from utilities import utils


class NameSpace(Resource):
    """
    NameSpace object, inherited from Resource.
    """
    def __init__(self, name):
        super(NameSpace, self).__init__()
        self.name = name
        self.namespace = self.name
        self.api_version = types.API_VERSION_V1
        self.kind = types.NAMESPACE

    def work_on(self):
        """
        Switch to name space

        Returns:
            bool: True f switched , False otherwise
        """
        return utils.run_command(command=f"oc project {self.name}")[0]
