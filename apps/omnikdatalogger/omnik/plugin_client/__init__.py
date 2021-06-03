class BaseClient(type):
    def __init__(cls, name, bases, attrs):
        super(BaseClient, cls).__init__(name)
        if not hasattr(cls, "client"):
            cls.client = []
        else:
            cls.register(cls)  # Called when a client class is imported

    def register(cls, client=None):
        cls.client.append(client())


class Client(object, metaclass=BaseClient):

    config = None
    logger = None
    hass_api = None
    use_timer = True
    plant_id_list = []

    def initialize(self):
        pass

    def terminate(self):
        pass
