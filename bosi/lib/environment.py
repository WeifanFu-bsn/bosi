# Copyright 2018 Big Switch Networks, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import constants as const
from helper import Helper
import os
from os import listdir
from os.path import isfile
from os.path import join
import re
from rest import RestLib


class Environment(object):
    def __init__(self, config, mode, fuel_cluster_id, rhosp, tag,
                 cleanup, skip_ivs_version_check, certificate_dir,
                 upgrade_dir, offline_dir, sriov, dpdk):
        # directory for upgrade
        self.upgrade_dir = None
        self.upgrade_pkgs = []
        if upgrade_dir:
            self.upgrade_dir = upgrade_dir
            self.upgrade_pkgs = [f for f in listdir(upgrade_dir) if isfile(join(upgrade_dir, f))]

        # directory for offline installation
        self.offline_dir = None
        self.offline_pkgs = []
        if offline_dir:
            self.offline_dir = offline_dir
            self.offline_pkgs = [f for f in listdir(offline_dir) if isfile(join(offline_dir, f))]

        # sriov for rhosp
        self.sriov = sriov

        # dpdk for rhosp p-only
        self.dpdk = dpdk

        # certificate directory
        self.certificate_dir = certificate_dir

        # fuel cluster id
        self.fuel_cluster_id = fuel_cluster_id

        # rhosp as installer
        self.rhosp = rhosp

        # tag, only deploy nodes with this tag
        self.tag = tag

        # clean up flag
        self.cleanup = cleanup

        self.skip_ivs_version_check = skip_ivs_version_check

        # pip proxy
        self.pip_proxy = config.get('pip_proxy')

        # neutron_id for ml2 plugin restproxy
        self.neutron_id = config.get('neutron_id')

        # tenant api version
        self.tenant_api_version = const.TENANT_NAME_API_VERSION

        # installer pxe interface ip
        self.installer_pxe_interface_ip = config.get(
            'installer_pxe_interface_ip')

        # install to specified nodes
        self.deploy_to_specified_nodes_only = config.get(
            'deploy_to_specified_nodes_only')

        # flags for upgrade
        self.install_ivs = True
        self.install_bsnstacklib = True
        self.install_all = True

        # setup node directory
        example_yamls = ["/usr/local/etc/bosi/config.yaml",
                         "/usr/etc/bosi/config.yaml"]
        for example_yaml in example_yamls:
            if os.path.isfile(example_yaml):
                self.setup_node_dir = os.path.dirname(example_yaml)
                break

        # t5 or t6 mode
        self.deploy_mode = const.MODE_DICT.get(mode)
        if not self.deploy_mode:
            self.deploy_mode = const.T5

        # flags for l3 agent
        self.deploy_l3_agent = False
        if self.deploy_mode == const.T5 and not fuel_cluster_id:
            self.deploy_l3_agent = True

        # flags for dhcp and metadata agent
        self.deploy_dhcp_agent = False
        if ((self.deploy_mode == const.T5 or self.deploy_mode == const.T6)
            and not fuel_cluster_id):
            self.deploy_dhcp_agent = True

        # selinux configuration
        self.selinux_mode = None

        # neutron vlan ranges
        self.network_vlan_ranges = config.get('network_vlan_ranges')
        network_vlan_range_pattern = re.compile(
            const.NETWORK_VLAN_RANGE_EXPRESSION, re.IGNORECASE)
        match = network_vlan_range_pattern.match(self.network_vlan_ranges)
        if not match:
            Helper.safe_print("network_vlan_ranges format is not correct.\n")
            exit(1)
        self.physnet = match.group(1)
        self.lower_vlan = match.group(2)
        self.upper_vlan = match.group(3)

        # bcf controller information
        self.bcf_version = config['bcf_version']
        self.bcf_controllers = config['bcf_controllers']
        self.bcf_controller_ips = []
        for controller in self.bcf_controllers:
            ip = controller.split(':')[0]
            self.bcf_controller_ips.append(ip)
        self.bcf_controller_user = config['bcf_controller_user']
        self.bcf_controller_passwd = config['bcf_controller_passwd']
        self.bcf_openstack_management_tenant = config.get(
            'bcf_openstack_management_tenant')

        # ivs pkg and debug pkg
        self.ivs_pkg_map = {}
        self.ivs_url_map = {}
        if config['ivs_packages']:
            for ivs_url in config['ivs_packages']:
                ivs_pkg = os.path.basename(ivs_url)
                if '.rpm' in ivs_pkg and 'debuginfo' not in ivs_pkg:
                    self.ivs_url_map['rpm'] = ivs_url
                    self.ivs_pkg_map['rpm'] = ivs_pkg
                elif '.rpm' in ivs_pkg and 'debuginfo' in ivs_pkg:
                    self.ivs_url_map['debug_rpm'] = ivs_url
                    self.ivs_pkg_map['debug_rpm'] = ivs_pkg
                elif '.deb' in ivs_pkg and 'dbg' not in ivs_pkg:
                    self.ivs_url_map['deb'] = ivs_url
                    self.ivs_pkg_map['deb'] = ivs_pkg
                elif '.deb' in ivs_pkg and 'dbg' in ivs_pkg:
                    self.ivs_url_map['debug_deb'] = ivs_url
                    self.ivs_pkg_map['debug_deb'] = ivs_pkg
                elif '.tar.gz' in ivs_pkg:
                    self.ivs_url_map['tar'] = ivs_url
                    self.ivs_pkg_map['tar'] = ivs_pkg

        # information will be passed on to nodes
        self.skip = False
        if 'default_skip' in config:
            self.skip = config['default_skip']
        self.os = config.get('default_os')
        self.os_version = config.get('default_os_version')
        if rhosp:
            self.os = const.REDHAT
            self.os_version = const.REDHAT_VERSIONS[0]
        self.role = config.get('default_role')
        self.user = config.get('default_user')
        # optional property, set default internally
        self.bond_mode = const.BondMode.STATIC
        if config.get('default_bond_mode'):
            self.bond_mode = const.BondMode[
                config.get('default_bond_mode').upper()]
        if rhosp:
            self.user = "heat-admin"
        elif fuel_cluster_id:
            self.user = "root"
        self.passwd = config.get('default_passwd')
        self.uplink_interfaces = config.get('default_uplink_interfaces')
        self.uplink_mtu = config.get('default_uplink_mtu')

        # openstack bsnstacklib version - applies to horizon plugin too
        self.openstack_release = str(config['openstack_release']).lower()
        array = self.bcf_version.split('.')
        if len(array) == 3:
            array = array[:-1]
        two_digit_bcfversion = '.'.join(array)

        self.bsnstacklib_version_lower = const.OS_BCF_MAPPING_LOWER[
            self.openstack_release][two_digit_bcfversion]
        self.bsnstacklib_version_upper = const.OS_BCF_MAPPING_UPPER[
            self.openstack_release][two_digit_bcfversion]

        # master bcf controller and cookie
        self.bcf_master = None
        self.bcf_cookie = None
        if fuel_cluster_id:
            self.bcf_master, self.bcf_cookie = (
                RestLib.get_active_bcf_controller(self.bcf_controller_ips,
                                                  self.bcf_controller_user,
                                                  self.bcf_controller_passwd))
            if (not self.bcf_master) or (not self.bcf_cookie):
                raise Exception("Failed to connect to master BCF controller, "
                                "quit setup.")

        # RHOSP 7 related config
        self.rhosp_automate_register = False
        if 'rhosp_automate_register' in config:
            self.rhosp_automate_register = config['rhosp_automate_register']
        self.rhosp_installer_management_interface = config.get(
            'rhosp_installer_management_interface')
        self.rhosp_installer_pxe_interface = config.get(
            'rhosp_installer_pxe_interface')
        self.rhosp_undercloud_dns = config.get('rhosp_undercloud_dns')
        self.rhosp_register_username = config.get('rhosp_register_username')
        self.rhosp_register_passwd = config.get('rhosp_register_passwd')

    def set_physnet(self, physnet):
        self.physnet = physnet

    def set_lower_vlan(self, lower_vlan):
        self.lower_vlan = lower_vlan

    def set_upper_vlan(self, upper_vlan):
        self.upper_vlan = upper_vlan

    def set_ivs_pkg_map(self, ivs_pkg):
        if '.rpm' in ivs_pkg and 'debuginfo' not in ivs_pkg:
            self.ivs_pkg_map['rpm'] = ivs_pkg
        elif '.rpm' in ivs_pkg and 'debuginfo' in ivs_pkg:
            self.ivs_pkg_map['debug_rpm'] = ivs_pkg
        elif '.deb' in ivs_pkg and 'dbg' not in ivs_pkg:
            self.ivs_pkg_map['deb'] = ivs_pkg
        elif '.deb' in ivs_pkg and 'dbg' in ivs_pkg:
            self.ivs_pkg_map['debug_deb'] = ivs_pkg
