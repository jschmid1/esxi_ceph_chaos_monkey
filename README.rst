

*****************
Description
*****************

This projects tries to stresstest a existing iSCSI and VMWare setup.

It

- Creates
- Migrates
- Clones
- Deletes

virtual machines.

During these operations it will simulate outages on the ceph cluster.

- Reboot a node
- Shutdown a OSD
- Reboot a iSCSI Gateway

It will stop and collect all necessary logs if either the ceph cluster
of the VMWare hosts report a failure.

Intended to run in a jenkins context, but can also be executed standalone.

For it to run you will need:

- running VMware cluster
- running ceph cluster
- configured datastore(iscsi)
- template vm to clone from


*****************
Installation
*****************

python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt
python3 stress_test_vmware_ceph/main.py

*****************
Configuration
*****************

Fill the config.yml with the required information.

.. code-block:: yaml

    mode: 'async' 
    # available modes are:
    # sync, async, mixed
    #
    # Logging
    LOG_LEVEL_CONSOLE: 'info'
    LOG_LEVEL_FILE: 'debug'
    LOG_LEVEL: 'info'
    LOG_FILE_PATH: 'chaos.log'

    # vshpere 
    host: "10.162.186.115"
    user: "root"
    password: "replace_me"
    dc_name: "Datacenter"
    cluster_name: "Openstack"
    esxi_hosts: ["10.162.186.111"]
    template_vm_name: "ceph_template_vm"

    # Ceph Admin
    ceph_adm_node: "blueshark1.arch.suse.de"
    ceph_adm_user: "root"
    ceph_adm_password: "replace_me"

    # Gateways
    gateways: ['blueshark2.arch.suse.de']
    gateway_user: "root"
    gateway_password: "replace_me"
    ds_names: ["iscsi_testing_1", "iscsi_testing_2"]

    # General settings
    filter_string: "ceph_"
    max_vms: 6
    max_tasks: 10
    wait_for_health_ok_t: 360
    force_reboot: False
    max_down_osds_ratio: 0.2
    MAX_DEPTH: 15
    chaos_rate: 500

****************
Validations
****************

Rebooting of a gateway will be disabled if you don't have more than one gateway defined in your configuration.
You can change that behavior by setting `force_reboot` to True.

----------

Migration can only be performed if there are multiple ( `esxi_hosts` or `ds_names` )

-----------

All you nodes (ceph admin node, gateways, vmware hosts, vcenter) need to be up and running before the stress test starts

-----------

The ammount of OSDs that will be taken down out/down is somewhat computed. The default is 20% based on.

`osd_count * 0.2`

You can change that 0.2 value with the `max_down_osds_ratio` config value

-----------

You can configure the amount of VMs spawned at the same point of time.
( You might want this if your vmware host is not _too_ strong, or you have other 
workload running at the same time.
Use `max_vms` for this.


*****************
Modes
*****************

There are 2(3) modes available currently.

  - sync:

  - async:
  - mixed:




*****************
Developed on
*****************

ESXI VMware version 6
pyvmomi (6.7.0)

There is no guarantee that other versions will work flawlessly

*****************
Disclaimer
*****************

This project is under development and can not be considered as stable.
It may cause high load on you VMWare instances and lead to failures.
Use it at you own risk 

