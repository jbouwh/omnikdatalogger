import json
from datetime import datetime

from omnik.plugins import Plugin

class PVOutput(Plugin):

  def process_message(self, **args):
    """
    Send data to pvoutput
    """
    now = datetime.utcnow()
    
    url = "http://pvoutput.org/service/r2/addstatus.jsp"

    _json = json.dumps(args['msg'], indent=2)

    self.logger.info('> Processing message: {}'.format(_json))

    