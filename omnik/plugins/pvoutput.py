from datetime import datetime

from plugins import Plugin

class PVOutput(Plugin):
  def __init__(self):
    super().__init__()
    self.description = 'Write output to PVOutput'

  def process_message(self, **args):
    """
    Send data to pvoutput
    """
    now = datetime.utcnow()
    
    url = "http://pvoutput.org/service/r2/addstatus.jsp"