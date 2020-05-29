class BaseClient(type):
    def __init__(cls, name, bases, attrs):
        super(BaseClient, cls).__init__(name)
        if not hasattr(cls, 'client'):
            cls.client = []
        else:
            cls.register(cls)  # Called when a client class is imported

    def register(cls, client):
        cls.client.append(client())


class Client(object, metaclass=BaseClient):

    config = None
    logger = None
    hass_api = None
    use_timer = True
    stoprequest = False

    def initialize(self):
        pass

    def stop(self):
        self.stoprequest = True
