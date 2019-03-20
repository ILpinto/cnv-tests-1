from .resource import Resource
from utilities import types


class Node(Resource):
    """
    NameSpace object, inherited from Resource.
    """
    def __init__(self, name=None, namespace=None):
        super(Node, self).__init__()
        self.name = name
        self.namespace = namespace
        self.api_version = types.API_VERSION_V1
        self.kind = types.NODE
