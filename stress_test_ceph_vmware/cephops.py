import ast
import logging
import random
import time
from colorama import Fore, Style
from config import Config
from utils import SshUtil, Utils

log = logging.getLogger(__name__)

class CephOps(Config):

    def __init__(self):
        Config.__init__(self)
        self.client = SshUtil(self.ceph_adm_node,
                              self.ceph_adm_user,
                              self.ceph_adm_password)
        self.utl = Utils(label="Waiting for {} ({}s)".format(self.ceph_health_is_ok_with,
                                                             self.wait_for_health_ok_t))
        self.down_osds = self.get_down_osds()
        self.out_osds = self.get_out_osds()
        self.osds = self.get_osd_ids()

    def random_osd(self):
        log.debug("Selecting random OSD")
        return random.choice(self.osds)

    def health_ok(self, silent=True):
        stdout, _ = self.client.run_cmd('ceph health')
        if stdout.startswith(self.ceph_health_is_ok_with):
            if silent:
                log.debug("Health is ok")
            else:
                log.info("Health is ok")
            return True
        if silent:
            log.debug("Health is not ok")
        else:
            log.info("Health is not ok")
        return False

    def set_noup(self):
        log.debug("Setting NoUp")
        stdout, _ = self.client.run_cmd('ceph osd set noup')

    def unset_noup(self):
        log.debug("Unsetting NoUp")
        stdout, _ = self.client.run_cmd('ceph osd unset noup')

    def get_down_osds(self):
        data, _ = self.client.run_cmd('ceph osd tree -f json')
        down_osds = []
        for node_osd in ast.literal_eval(data)['nodes']:
            if node_osd.get('type') == 'osd' and 'osd' in node_osd.get('name'):
                if node_osd.get('status') == 'down':
                    down_osds.append(node_osd.get('id'))
        return down_osds

    def get_out_osds(self):
        data, _ = self.client.run_cmd('ceph osd tree -f json')
        out_osds = []
        for node_osd in ast.literal_eval(data)['nodes']:
            if node_osd.get('type') == 'osd' and 'osd' in node_osd.get('name'):
                if node_osd.get('reweight') != 1.0:
                    out_osds.append(node_osd.get('id'))
        return out_osds

    @property
    def max_down_osds(self):
        # Allow to have max 20% osds down
        return int(len(self.osds) * self.max_down_osds_ratio)

    @property
    def osd_down_count(self):
        return len(self.down_osds)

    @property
    def osd_out_count(self):
        return len(self.out_osds)

    def wait_for_health_ok(self, silent=True):
        """Wait for $timeout until ceph cluster is back to HEALTH_OK/WARN again
        """
        start = time.time()
        timeout = start + self.wait_for_health_ok_t
        health_ok = False
        while not health_ok:
            if not silent:
                self.utl.spinner()
            if self.health_ok():
                end = time.time()
                log.info("Ceph's health is okay after {} seconds".format(round(end - start, 4)))
                health_ok = True
            if time.time() > timeout:
                health_ok = False
            time.sleep(5)
        return health_ok

    def get_osd_ids(self):
        log.debug("Scraping OSDs")
        ids, _ = self.client.run_cmd('ceph osd ls -f json')
        return ast.literal_eval(ids)

    def mark_osd(self, osd_id, state):
        cmd = "ceph osd {} {}".format(state, osd_id)
        stdout, stderr = self.client.run_cmd(cmd)
        if stderr:
            log.info(stderr)
        if not stderr and stdout != 'marked {} osd.{}.'.format(state, osd_id):
            log.info(stdout)


