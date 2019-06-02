from cachetools import TTLCache

class PluginMount(type):
  def __init__(cls, name, bases, attrs):
    super(PluginMount, cls).__init__(name)
    if not hasattr(cls, 'plugins'):
      cls.plugins = []
    else:
      cls.register_plugin(cls) # Called when a plugin class is imported

  def register_plugin(cls, plugin):
    cls.plugins.append(plugin())

class Plugin(object):
  __metaclass__ = PluginMount
  
  config = None
  logger = None

class CachedPlugin(object):
  __metaclass__ = PluginMount
  
  config = None
  logger = None

  cache = TTLCache(maxsize=1, ttl=300)