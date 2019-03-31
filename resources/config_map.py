from utilities import types
from .resource import Resource


class ConfigMap(Resource):
    """
    ConfigMap object, inherited from Resource.
    """
    def __init__(self, name, namespace):
        super(ConfigMap, self).__init__()
        self.name = name
        self.namespace = namespace
        self.api_version = types.API_VERSION_V1
        self.kind = types.CONFIG_MAP
