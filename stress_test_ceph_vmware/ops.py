import logging
import random
import string
from config import Config
from utils import Utils
from connect import Connect
from colorama import Fore, Style
from pyVmomi import vim, vmodl
from task_queue import Queue

log = logging.getLogger(__name__)

class Ops(Config):

    def __init__(self):
        Config.__init__(self)
        self.si = Connect().si
        self.utl = Utils(label='wait')
        self.queue = Queue()
        self.content = self.si.RetrieveContent()
        self.vms = []
        self.MAX_DEPTH = 10
        self.migration_between_hosts = self.migration_possible(self.esxi_hosts)
        self.migration_between_datasources = self.migration_possible(self.ds_names)

    def migration_possible(self, source):
        if len(source) > 1:
            return True
        return False

    def generate_name(self, N=7):
        return self.filter_string + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))

    def random_datastore(self):
        return random.choice(self.ds_names)

    def random_gateway(self):
        return random.choice(self.gateways)

    def random_host(self):
        return random.choice(self.esxi_hosts)

    @property
    def powered_on_vms(self):
        return [x for x in self.vms if x.runtime.powerState == 'poweredOn']

    @property
    def powered_off_vms(self):
        return [x for x in self.vms if x.runtime.powerState == 'poweredOff']

    def vm_is_off(self, vm):
        if vm.runtime.powerState == "poweredOff":
            return True
        return False

    def vm_is_on(self, vm):
        if vm.runtime.powerState == "poweredOn":
            return True
        return False

    def poweroff_vm(self, vm):
        if self.vm_is_on(vm):
            log.debug("Powering off VM {}".format(vm))
            self.queue.push_task(vm.PowerOffVM_Task())
        return True

    def poweron_vm(self, vm):
        if self.vm_is_off(vm):
            log.debug("Powering on VM {}".format(vm))
            self.queue.push_task(vm.PowerOnVM_Task())
        return True

    def get_ip_addr(self, vm):
        return vm.guest.ipAddress

    def get_vm_list(self):
        for child in self.content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                datacenter = child
                vmfolder = datacenter.vmFolder
                vmlist = vmfolder.childEntity
                for vm in vmlist:
                    self.store_vminfo(vm, filter_='ceph')

    def store_vminfo(self, vm, filter_=None, depth=1):
        """
        Print information for a particular virtual machine or recurse into a folder
        with depth protection. There has to be a better way of filtering.
        """

        # if this is a group it will have children. if it does, recurse into them
        # and then return
        if hasattr(vm, 'childEntity'):
            if depth > self.MAX_DEPTH:
                return
            vmlist = vm.childEntity
            for child in vmlist:
                self.store_vminfo(child, filter_=filter_, depth=depth+1)
            return
        try:
            name = vm.summary.config.name
        except:
            logging.debug("Vm is already gone or does not exist yet.")
            return False
        if name.startswith(filter_) and not name == self.template_vm_name and not self.has_deletion_task(vm) and not self.has_clone_task(vm) and not vm in self.vms and vm.summary.runtime.host:
            # Don't add if still creating
            self.vms.append(vm)

    def get_obj(self, vimtype, name):
        """
        Return an object by name, if name is None the
        first found object is returned
        """
        obj = None
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)
        for c in container.view:
            if name:
                if c.name == name:
                    obj = c
                    break
            else:
                obj = c
                break
        return obj

    def clone_vm(self, power_on=True):
        """
        Clone a VM from a template/VM
        """
        vm_name = self.generate_name()
        ds_name = self.random_datastore()
        host_name = self.random_host()


        # Collect needed objects
        datacenter = self.get_obj([vim.Datacenter], self.dc_name)
        datastore = self.get_obj([vim.Datastore], ds_name)
        cluster = self.get_obj([vim.ClusterComputeResource], self.cluster_name)
        host = self.get_obj([vim.HostSystem], host_name)
        resource_pool = cluster.resourcePool
        template = self.get_obj([vim.VirtualMachine], self.template_vm_name)
        destfolder = datacenter.vmFolder

        # any of .datastores. Currently only checking for [0]
        if template.datastore[0].summary.name != ds_name:
            log.info(Fore.CYAN+ "Detected a migration between datastores")

        if template.summary.runtime.host.name != host_name:
            log.info(Fore.CYAN+ "Detected a migration between hosts")

        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = resource_pool
        relospec.host = host

        clonespec = vim.vm.CloneSpec()
        clonespec.location = relospec
        clonespec.powerOn = power_on

        log.info(Style.BRIGHT + "Cloning...")

        task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
        self.queue.push_task(task)
        self.get_vm_list()


    def overall_tasks(self, silent=True):
        taskManager = self.si.content.taskManager
        for task in taskManager.recentTask:
            if task.info.state == 'running':
                # curcument the push_tasks check
                if not silent:
                    log.info(Fore.YELLOW + "Found old tasks that need to finish before adding new.")
                    log.info(Fore.YELLOW + "Task: for {}".format(task.info.task.info.descriptionId))
                self.queue.tasks.append(task.info.task)
        log.info("You currently have {} tasks running".format(self.queue.task_count))

    def get_task_history(self, vm):
        """
        50% dead code.. might be replaced by overall_tasks()
        """
        taskManager = self.si.content.taskManager
        filterspec = vim.TaskFilterSpec()
        filterspec.entity = vim.TaskFilterSpec.ByEntity(entity=vm,recursion='all')
        try:
            collector = taskManager.CreateCollectorForTasks(filterspec)
        except:
            log.debug("Could not instantiate collector. retrying..")
            return [], []
        prev_tasks = collector.ReadPrev(4)
        next_tasks = collector.ReadNext(4)
        return prev_tasks, next_tasks

    def has_deletion_task(self, vm):
        prev_tasks, next_tasks = self.get_task_history(vm)
        for task in next_tasks:
            if vm.summary.config.name == task.entityName and task.descriptionId == 'VirtualMachine.destroy':
                logging.debug("Detected a deletion task for VM {}".format(vm))
                return True

    def has_clone_task(self, vm):
        prev_tasks, next_tasks = self.get_task_history(vm)
        for task in next_tasks:
            if vm.summary.config.name == task.entityName and task.descriptionId == 'VirtualMachine.destroy':
                logging.debug("Detected a clone task for VM {}".format(vm))
                return True

    def destroy_vm(self, vm):
        if isinstance(vm, str):
            vm = self.get_obj([vim.VirtualMachine], vm)
        try:
            vm_name = vm.name
            log.info(Style.BRIGHT + "Removing VM {} - {}".format(vm, vm_name))
        except:
            log.warning(Fore.RED + "There was something wrong with VM retrieval. Trying again")
            self.vms.remove(vm)
            return False
        if vm.runtime.powerState == "poweredOn":
            self.queue.push_task(vm.PowerOffVM_Task())
        self.queue.push_task(vm.Destroy_Task())
        self.vms.remove(vm)
        self.get_vm_list()

    def create_dummy_vm(self, vm_name, datastore):
        """Creates a dummy VirtualMachine with 1 vCpu, 128MB of RAM.
        :param name: String Name for the VirtualMachine
        :param datastore: DataStrore to place the VirtualMachine on
        """
        datastore_path = '[' + datastore + '] ' + vm_name
        datacenter = self.get_obj([vim.Datacenter], self.dc_name)
        hosts = datacenter.hostFolder.childEntity
        resource_pool = hosts[0].resourcePool
        vmfolder = datacenter.vmFolder

        # bare minimum VM shell, no disks. Feel free to edit
        vmx_file = vim.vm.FileInfo(logDirectory=None, snapshotDirectory=None,
                                   suspendDirectory=None,
                                   vmPathName=datastore_path)

        config = vim.vm.ConfigSpec(name=vm_name, memoryMB=128, numCPUs=1,
                                   files=vmx_file, guestId='dosGuest',
                                   version='vmx-07')

        log.info("Creating VM {}...".format(vm_name))
        task = vmfolder.CreateVM_Task(config=config, pool=resource_pool)
        self.queue.push_task(task)


