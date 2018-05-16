#!/usr/bin/env python3
"""
Test
"""
from __future__ import print_function
import sys
import random
import logging
# external modules
from colorama import Fore, Style, init
from pyVmomi import vim, vmodl
# custom modules
from cephops import CephOps
from config import Config
from utils import _setup_logging, Utils, SshUtil
from vmwareops import VMwareOps
from ops import Ops
from thread import start_thread

log = logging.getLogger(__name__)

class Runner(Config):

    def __init__(self):
        log.debug("Initialized Runner")
        Config.__init__(self)
        self.ops = Ops()
        self.cephops = CephOps()
        self.vmwareops = VMwareOps()
        self.ops.get_vm_list()

        if len(self.gateways) < 2:
            self.reboot_allowed = False
        if self.force_reboot:
            self.reboot_allowed = True

    def hosts_up(self):
        """
        Check if all sources like (gateways, vmware, cephadm) are up.
        """
        log.info("Perfoming intial availability check for hosts.")
        state = True
        for gateway in self.gateways:
            ssh_ = SshUtil(gateway,
                           self.gateway_user,
                           self.gateway_password)
            try:
                log.debug("Checking gateway {} for availability".format(gateway))
                ssh_.run_cmd('ls')
            except:
                log.critical("Unexpected error: {}".format(sys.exc_info()[0]))
                log.critical(Fore.RED + "The gateway {} is not reachable".format(gateway))
                state = False
        return state

    def startup(self):
        log.debug("Startup sequence..")
        if not self.hosts_up():
            sys.exit(1)
        self.ops.get_vm_list()
        self.ops.overall_tasks(silent=False)
        # Danger zone.. Remove after development
        if self.ops.queue.task_count >= 50:
            self.ops.queue.cancel_all_tasks()

        if not self.ops.migration_between_hosts:
            log.warning(Fore.YELLOW + " * There is no migration between hosts possible. You only provided one host in your config")
        if not self.ops.migration_between_datasources:
            log.warning(Fore.YELLOW + " * There is no migration between datasources possible. You only provided one datasource in your config")
        if self.mode == 'sync':
            log.warning(Fore.YELLOW + " * You are running in syncronous mode. Tasks will be handled sequentially")
        if self.mode == 'async':
            log.warning(Fore.YELLOW + " * You are running in async mode. Tasks will be put in a queue up to 'max_queue' ( UNDER DEVELOPMENT )")
        if self.mode == 'mixed':
            log.warning(Fore.YELLOW + " * You are running in mixed mode. Tasks will be put in a queue up to 'max_queue' and are subsequently processed until the queue is empty ( UNDER DEVELOPMENT )")

        if not self.vmwareops.health_ok():
            log.critical(Fore.RED + "Your vmwarecluster cluster is not in HEALTH_OK state.")
            sys.exit(1)

        if not self.cephops.health_ok(silent=False):
            log.critical(Fore.RED + "Your ceph cluster is not in HEALTH_OK state.")
            sys.exit(1)

    def print_header(self):
        print("=================================")
        print("\n")

    def print_footer(self):
        print("\n")
        print("=================================")

    def check_thresholds(self):
        log.debug("Checking thresholds")
        if len(self.ops.vms) < self.max_vms:
            # Spawn until threshold is fulfilled again
            while len(self.ops.vms) < self.max_vms:
                log.info(Fore.YELLOW + "VM count dropped below the configured threshold. Filling up")
                self.ops.clone_vm()

        if len(self.ops.vms) > self.max_vms:
            while len(self.ops.vms) > self.max_vms:
                log.info(Fore.YELLOW + "VM count rose over the configured threshold. Removing VMs")
                self.destroy_vms(count=1)

        if self.cephops.osd_out_count > self.cephops.max_down_osds:
            log.info(Fore.YELLOW + "Down OSDs count dropped below the configured thereshold. Adding back in.")
            for osd_id in self.cephops.out_osds:
                self.cephops.mark_osd(osd_id, 'in')

    def destroy_vms(self, count=0):
        # If a new VM gets added to the .vms list, it will be appended.
        # Which means that it will be appended to the end of the list.
        # Iterations with the 'in' operator starts at the beginning of the list
        # which means that I'll delete the oldest first. That's good.
        count = count
        while count > 0:
            for vm in self.ops.vms:
                self.ops.destroy_vm(vm)
                break
            count -= 1

    def copy_vmware_logs(self):
        # Refactor to one method
        files = ['/var/log/vmkernel.log']
        timestamp = time.time()
        for host in self.esxi_hosts:
            log.info("Collecting logs from {}".format(host))
            ssh = SshUtil(host, self.user, self.password)
            for fn in files:
                log.info("Collecting {}".format(fn))
                ssh.copy_file_from_host(fn, 'logs/{}'.format(fn+timestamp))

    def copy_gateway_logs(self):
        # Refactor to one method
        files = ['/var/log/messages']
        timestamp = time.time()
        for host in self.gateways:
            log.info("Collecting logs from {}".format(host))
            ssh = SshUtil(host, self.gateway_user, self.gateway_password)
            for fn in files:
                log.info("Collecting {}".format(fn))
                ssh.copy_file_from_host(fn, 'logs/{}'.format(fn+timestamp))

    def teardown(self):
        self.copy_vmware_logs()
        self.copy_gateway_logs()

    def stress_test(self):
        self.startup()
        abort = False
        while not abort:
            self.ops.queue.wait_for_any_finished_task()
            self.print_header()
            self.check_thresholds()
            seed = random.randrange(0,500)
            log.debug("seed: {}".format(seed))
            if seed in range(0,99):
                self.ops.clone_vm()

            if seed in range(100,199):
                self.destroy_vms(count=1)

            if seed in range(200,299):
                self.ops.clone_vm()

            if seed in range(300,320):
                gateway = self.ops.random_gateway()
                # Reboot in theory. but for now fake the call
                #SshUtil(gateway, self.gateway_user, self.gateway_password, self.reboot_allowed).reboot()
                log.info(Style.DIM + "This would reboot a gateway")

            if seed in range(321,399):
                random_osd = self.cephops.random_osd()
                self.cephops.mark_osd(random_osd, 'out')

            if seed in range(400,500):
                log.info(Fore.RED + "Placeholder .. What to do more?")

            if not self.cephops.wait_for_health_ok(silent=False):
                log.info(Fore.RED + "Health of Ceph is not ok, aborting")
                abort = True

            if not self.vmwareops.health_ok():
                log.info(Fore.RED + "Health of VMWARE is not ok, aborting")
                abort = True
            self.print_footer()
            
        if abort:
            self.teardown()

def main():
    # For colorama
    init(autoreset=True)
    # Logging
    _setup_logging()
    # Run mainloop
    Runner().stress_test()

if __name__ == '__main__':
    main()
