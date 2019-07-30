# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2019 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the "License");
# you may not use this software except in compliance with the License.
# You may obtain a copy of the License at
#
#             http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#
# Unless otherwise specified, all documentation contained herein is licensed
# under the Creative Commons License, Attribution 4.0 Intl. (the "License");
# you may not use this documentation except in compliance with the License.
# You may obtain a copy of the License at
#
#             https://creativecommons.org/licenses/by/4.0/
#
# Unless required by applicable law or agreed to in writing, documentation
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ============LICENSE_END============================================
#
#

import json
import os

from preload import (
    AbstractPreloadGenerator,
    get_json_template,
    get_or_create_template,
    replace,
)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "vnfapi_data")


def add_fixed_ips(network_template, port):
    for ip in port.fixed_ips:
        if ip.ip_version == 4:
            network_template["network-ips"].append({"ip-address": replace(ip.param)})
            network_template["ip-count"] += 1
        else:
            network_template["network-ips-v6"].append({"ip-address": replace(ip.param)})
            network_template["ip-count-ipv6"] += 1


def add_floating_ips(network_template, network):
    # only one floating IP is really supported, in the preload model
    # so for now we'll just use the last one.  We might revisit this
    # and if multiple floating params exist, then come up with an
    # approach to pick just one
    for ip in network.floating_ips:
        key = "floating-ip" if ip.ip_version == 4 else "floating-ip-v6"
        network_template[key] = replace(ip.param)


def get_or_create_network_template(network_role, vm_networks):
    """
    If the network role already exists in vm_networks, then
    return that otherwise create a blank template and return that
    """
    return get_or_create_template(
        DATA_DIR, "network-role", network_role, vm_networks, "vm-network"
    )


class VnfApiPreloadGenerator(AbstractPreloadGenerator):
    @classmethod
    def supports_output_passing(cls):
        return False

    @classmethod
    def format_name(cls):
        return "VNF-API"

    @classmethod
    def output_sub_dir(cls):
        return "vnfapi"

    def generate_module(self, vnf_module):
        preload = get_json_template(DATA_DIR, "preload_template")
        self._populate(preload, vnf_module)
        outfile = "{}/{}.json".format(self.output_dir, vnf_module.vnf_name)
        with open(outfile, "w") as f:
            json.dump(preload, f, indent=4)

    def _populate(self, preload, vnf_module):
        self._add_availability_zones(preload, vnf_module)
        self._add_vnf_networks(preload, vnf_module)
        self._add_vms(preload, vnf_module)
        self._add_parameters(preload, vnf_module)

    @staticmethod
    def _add_availability_zones(preload, vnf_module):
        zones = preload["input"]["vnf-topology-information"]["vnf-assignments"][
            "availability-zones"
        ]
        for zone in vnf_module.availability_zones:
            zones.append({"availability-zone": replace(zone)})

    @staticmethod
    def _add_vnf_networks(preload, vnf_module):
        networks = preload["input"]["vnf-topology-information"]["vnf-assignments"][
            "vnf-networks"
        ]
        for network in vnf_module.networks:
            network_data = {
                "network-role": network.network_role,
                "network-name": replace(
                    "network name for {}".format(network.name_param)
                ),
            }
            for subnet in network.subnet_params:
                key = "ipv6-subnet-id" if "_v6_" in subnet else "subnet-id"
                network_data[key] = subnet
            networks.append(network_data)

    @staticmethod
    def _add_vms(preload, vnf_module):
        vm_list = preload["input"]["vnf-topology-information"]["vnf-assignments"][
            "vnf-vms"
        ]
        for vm in vnf_module.virtual_machine_types:
            vm_template = get_json_template(DATA_DIR, "vm")
            vm_template["vm-type"] = vm.vm_type
            vm_template["vm-count"] = vm.vm_count
            vm_template["vm-names"]["vm-name"].extend(map(replace, vm.names))
            vm_list.append(vm_template)
            vm_networks = vm_template["vm-networks"]
            for port in vm.ports:
                role = port.network.network_role
                network_template = get_or_create_network_template(role, vm_networks)
                network_template["network-role"] = role
                network_template["network-role-tag"] = role
                network_template["use-dhcp"] = "Y" if port.uses_dhcp else "N"
                add_fixed_ips(network_template, port)
                add_floating_ips(network_template, port)

    @staticmethod
    def _add_parameters(preload, vnf_module):
        params = preload["input"]["vnf-topology-information"]["vnf-parameters"]
        for key, value in vnf_module.preload_parameters.items():
            params.append({"vnf-parameter-name": key, "vnf-parameter-value": value})
