from cachetools import TTLCache

# TODO: Create Abstract Base Class
class BasePlugin(type):
  def __init__(cls, name, bases, attrs):
    super(BasePlugin, cls).__init__(name)
    if not hasattr(cls, 'plugins'):
      cls.plugins = []
    else:
      cls.register(cls) # Called when a plugin class is imported

  def register(cls, plugin):
    cls.plugins.append(plugin())

class Plugin(object, metaclass=BasePlugin):
  
  config = None
  logger = None

  cache  = TTLCache(maxsize=1, ttl=300)