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
import json
import os

from preload import (
    AbstractPreloadGenerator,
    get_or_create_template,
    get_json_template,
    replace,
)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "grapi_data")


def get_or_create_network_template(network, vm_networks):
    """
    If the network role already exists in vm_networks, then
    return that otherwise create a blank template and return that
    """
    return get_or_create_template(
        DATA_DIR, "network-role", network, vm_networks, "vm-network"
    )


def add_fixed_ips(network_template, fixed_ips, uses_dhcp):
    items = network_template["network-information-items"]["network-information-item"]
    ipv4s = next(item for item in items if item["ip-version"] == "4")
    ipv6s = next(item for item in items if item["ip-version"] == "6")
    if uses_dhcp:
        ipv4s["use-dhcp"] = "Y"
        ipv6s["use-dhcp"] = "Y"
    for ip in fixed_ips:
        target = ipv4s if ip.ip_version == 4 else ipv6s
        ips = target["network-ips"]["network-ip"]
        if ip.param not in ips:
            ips.append(replace(ip.param))
        target["ip-count"] += 1


def add_floating_ips(network_template, floating_ips):
    for ip in floating_ips:
        key = "floating-ip-v4" if ip.ip_version == 4 else "floating-ip-v6"
        ips = network_template["floating-ips"][key]
        if ip.param not in ips:
            ips.append(replace(ip.param))


class GrApiPreloadGenerator(AbstractPreloadGenerator):
    @classmethod
    def supports_output_passing(cls):
        return True

    @classmethod
    def format_name(cls):
        return "GR-API"

    @classmethod
    def output_sub_dir(cls):
        return "grapi"

    def generate_module(self, vnf_module):
        template = get_json_template(DATA_DIR, "preload_template")
        self._populate(template, vnf_module)
        vnf_name = vnf_module.vnf_name
        outfile = "{}/{}.json".format(self.output_dir, vnf_name)
        with open(outfile, "w") as f:
            json.dump(template, f, indent=4)

    def _populate(self, preload, vnf_module):
        self._add_vnf_metadata(preload)
        self._add_vms(preload, vnf_module)
        self._add_availability_zones(preload, vnf_module)
        self._add_parameters(preload, vnf_module)
        self._add_vnf_networks(preload, vnf_module)

    @staticmethod
    def _add_vms(preload, vnf_module):
        vms = preload["input"]["preload-vf-module-topology-information"][
            "vf-module-topology"
        ]["vf-module-assignments"]["vms"]["vm"]
        for vm in vnf_module.virtual_machine_types:
            vm_template = get_json_template(DATA_DIR, "vm")
            vms.append(vm_template)
            vm_template["vm-type"] = vm.vm_type
            vm_template["vm-names"]["vm-name"].extend(map(replace, vm.names))
            vm_template["vm-count"] = vm.vm_count
            vm_networks = vm_template["vm-networks"]["vm-network"]
            for port in vm.ports:
                role = port.network.network_role
                network_template = get_or_create_network_template(role, vm_networks)
                network_template["network-role"] = role
                add_fixed_ips(network_template, port.fixed_ips, port.uses_dhcp)
                add_floating_ips(network_template, port.floating_ips)

    @staticmethod
    def _add_availability_zones(preload, vnf_module):
        zones = preload["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["availability-zones"]["availability-zone"]
        zones.extend(map(replace, vnf_module.availability_zones))

    @staticmethod
    def _add_parameters(preload, vnf_module):
        params = [
            {"name": key, "value": value}
            for key, value in vnf_module.parameters.items()
        ]
        preload["input"]["preload-vf-module-topology-information"][
            "vf-module-topology"
        ]["vf-module-parameters"]["param"].extend(params)

    @staticmethod
    def _add_vnf_networks(preload, vnf_module):
        networks = preload["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["vnf-networks"]["vnf-network"]
        for network in vnf_module.networks:
            network_data = {
                "network-role": network.network_role,
                "network-name": replace(network.name_param),
            }
            if network.subnet_params:
                network_data["subnets-data"] = {"subnet-data": []}
                subnet_data = network_data["subnets-data"]["subnet-data"]
                for subnet_param in network.subnet_params:
                    subnet_data.append({"subnet-id": replace(subnet_param)})
            networks.append(network_data)

    @staticmethod
    def _add_vnf_metadata(preload):
        topology = preload["input"]["preload-vf-module-topology-information"]
        vnf_meta = topology["vnf-topology-identifier-structure"]
        vnf_meta["vnf-name"] = replace("vnf_name")
        vnf_meta["vnf-type"] = replace("Concatenation of "
                                       "<Service Name>/<VF Instance Name> "
                                       "MUST MATCH SDC")
        module_meta = topology["vf-module-topology"]["vf-module-topology-identifier"]
        module_meta["vf-module-name"] = replace("vf_module_name")
        module_meta["vf-module-type"] = replace("<vfModuleModelName> from CSAR or SDC")
