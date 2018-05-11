from setuptools import setup, find_packages
setup(
    name="stress_test_vmware_ceph",
    version="0.1",
    packages=find_packages(),
    install_requires=['pyvmomi', 'colorama', 'paramiko'],
    author="Joshua Schmid",
    author_email="jschmid@suse.com",
    description="Stress testing vmware with a iscsi datastore from ceph",
)
