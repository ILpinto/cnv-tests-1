from utilities import types, utils

from .resource import Resource


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
        return utils.run_oc_command(command=f"project {self.name}")[0]
