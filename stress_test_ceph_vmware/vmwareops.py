import logging
from config import Config
from utils import SshUtil

log = logging.getLogger(__name__)

class VMwareOps(Config):

    def __init__(self):
        log.debug("Initialized VMwareOps")
        Config.__init__(self)

    def clients(self):
        for node in self.esxi_hosts:
            yield SshUtil(self.host,
                          self.user,
                          self.password)

    def health_ok(self):
        """ Not sure if that makes sense
        """
        for client in self.clients():
            if client.run_cmd('ls'):
                log.info('Vmware cluster is up.')
                return True
            else:
                return False
