class Plugin(object):
  """
  Base class
  """
  def __init__(self)
    self.description = 'UNKNOWN'

  def process_message(self, **args):
    raise NotImplementedError