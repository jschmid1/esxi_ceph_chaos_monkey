import yaml
from customexceptions import NotImplemented

class Config(object):

    def __init__(self):
        self.path = 'config.yml'
        self.cnt = self.load_cfg()
        self.mode = self.cnt.get('mode', 'sync')
        self.max_tasks = int(self.cnt.get('max_tasks', 5))
        if self.mode == 'sync':
            self.max_tasks = 0
        self.LOG_LEVEL_FILE = self.cnt.get('LOG_LEVEL_FILE', 'debug')
        self.LOG_LEVEL_CONSOLE = self.cnt.get('LOG_LEVEL_CONSOLE', 'info')
        self.LOG_LEVEL = self.cnt.get('LOG_LEVEL', 'info')
        self.LOG_FILE_PATH = self.cnt.get('LOG_FILE_PATH', 'info')
        self.host = self.cnt.get('host', None)
        self.user = self.cnt.get('user', None)
        self.password = self.cnt.get('password', None)
        self.dc_name = self.cnt.get('dc_name', 'Datacenter')
        self.ds_names = self.cnt.get('ds_names', [])
        self.esxi_hosts = self.cnt.get('esxi_hosts', [])
        self.ceph_adm_node = self.cnt.get('ceph_adm_node', None)
        self.ceph_adm_user = self.cnt.get('ceph_adm_user', None)
        self.ceph_adm_password = self.cnt.get('ceph_adm_password', None)
        self.gateways = self.cnt.get('gateways', [])
        self.gateway_user = self.cnt.get('gateway_user', None)
        self.gateway_password = self.cnt.get('gateway_password', None)
        self.cluster_name = self.cnt.get('cluster_name', 'Openstack')
        self.filter_string = self.cnt.get('filter_string', 'ceph_')
        self.template_vm_name = self.cnt.get('template_vm_name', '')
        self.ceph_health_is_ok_with = self.cnt.get('ceph_health_is_ok_with', 'HEALTH_OK')
        self.max_vms = int(self.cnt.get('max_vms', 5))
        self.chaos_rate = int(self.cnt.get('chaos_rate', 500))
        self.wait_for_health_ok_t = int(self.cnt.get('wait_for_health_ok_t', 360))
        self.MAX_DEPTH = int(self.cnt.get('max_depth', 15))
        self.max_down_osds_ratio = float(self.cnt.get('max_down_osds_ratio', 0.2))
        self.force_reboot = bool(self.cnt.get('force_reboot', False))

    def verify_config(self):
        if self.mode == 'mixed':
            raise NotImplemented("Mixed is not implemented yet")

    def load_cfg(self):
        with open(self.path, 'r') as _fd:
            return yaml.load(_fd)
