

class LocalProxyBasePlugin(type):
    def __init__(cls, name, bases, attrs):
        super(LocalProxyBasePlugin, cls).__init__(name)
        if not hasattr(cls, 'localproxy_plugins'):
            cls.localproxy_plugins = []
        else:
            cls.register(cls)  # Called when a plugin class is imported

    def register(cls, plugin):
        cls.localproxy_plugins.append(plugin())


class LocalProxyPlugin(object, metaclass=LocalProxyBasePlugin):

    config = None
    logger = None
    hass_api = None
    semaphore = None
    client = None

    def terminate(self):
        pass
