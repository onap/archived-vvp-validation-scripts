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
from pathlib import Path
from typing import Mapping

from preload.data import AbstractPreloadInstance
from preload.generator import (
    get_json_template,
    get_or_create_template,
    AbstractPreloadGenerator,
)
from preload.model import VnfModule, Port

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

    def generate_module(
        self,
        vnf_module: VnfModule,
        preload_data: AbstractPreloadInstance,
        output_dir: Path,
    ):
        self.module_incomplete = False
        template = get_json_template(DATA_DIR, "preload_template")
        self._populate(template, preload_data, vnf_module)
        incomplete = (
            "_incomplete"
            if preload_data.flag_incompletes and self.module_incomplete
            else ""
        )
        filename = "{}{}.json".format(preload_data.preload_basename, incomplete)
        outfile = output_dir.joinpath(filename)
        with outfile.open("w") as f:
            json.dump(template, f, indent=4)

    def _populate(
        self,
        template: Mapping,
        preload_data: AbstractPreloadInstance,
        vnf_module: VnfModule,
    ):
        self._add_vnf_metadata(template, preload_data)
        self._add_availability_zones(template, preload_data, vnf_module)
        self._add_vnf_networks(template, preload_data, vnf_module)
        self._add_vms(template, preload_data, vnf_module)
        self._add_parameters(template, preload_data, vnf_module)

    def _add_vnf_metadata(self, template: Mapping, preload: AbstractPreloadInstance):
        topology = template["input"]["preload-vf-module-topology-information"]
        vnf_meta = topology["vnf-topology-identifier-structure"]
        vnf_meta["vnf-name"] = self.normalize(preload.vnf_name, "vnf_name")
        vnf_meta["vnf-type"] = self.normalize(
            preload.vnf_type,
            "vnf-type",
            "VALUE FOR: Concatenation of <Service Name>/"
            "<VF Instance Name> MUST MATCH SDC",
        )
        module_meta = topology["vf-module-topology"]["vf-module-topology-identifier"]
        module_meta["vf-module-name"] = self.normalize(
            preload.vf_module_name, "vf_module_name"
        )
        module_meta["vf-module-type"] = self.normalize(
            preload.vf_module_model_name,
            "vf-module-model-name",
            "VALUE FOR: <vfModuleModelName> from CSAR or SDC",
        )

    def _add_availability_zones(
        self, template: Mapping, preload: AbstractPreloadInstance, vnf_module: VnfModule
    ):
        zones = template["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["availability-zones"]["availability-zone"]
        for i, zone_param in enumerate(vnf_module.availability_zones):
            zone = preload.get_availability_zone(i, zone_param)
            zones.append(self.normalize(zone, zone_param, index=i))

    def _add_vnf_networks(
        self, template: Mapping, preload: AbstractPreloadInstance, vnf_module: VnfModule
    ):
        networks = template["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["vnf-networks"]["vnf-network"]
        for network in vnf_module.networks:
            network_data = {
                "network-role": network.network_role,
                "network-name": self.normalize(
                    preload.get_network_name(network.network_role, network.name_param),
                    network.name_param,
                    "VALUE FOR: network name of {}".format(network.name_param),
                ),
            }
            if network.subnet_params:
                network_data["subnets-data"] = {"subnet-data": []}
                subnet_data = network_data["subnets-data"]["subnet-data"]
                for subnet in network.subnet_params:
                    data = {}
                    subnet_id = preload.get_subnet_id(
                        network.network_role, subnet.ip_version, subnet.param_name
                    )
                    if subnet_id:
                        data["subnet-id"] = self.normalize(subnet_id, subnet.param_name)
                    else:
                        subnet_name = preload.get_subnet_name(
                            network.network_role, subnet.ip_version, ""
                        )
                        data["subnet-name"] = self.normalize(
                            subnet_name,
                            subnet.param_name,
                            alt_message="VALUE FOR: name of {}".format(
                                subnet.param_name
                            ),
                        )
                    subnet_data.append(data)
            networks.append(network_data)

    def add_floating_ips(
        self, network_template: dict, port: Port, preload: AbstractPreloadInstance
    ):
        for ip in port.floating_ips:
            key = "floating-ip-v4" if ip.ip_version == 4 else "floating-ip-v6"
            ips = network_template["floating-ips"][key]
            value = self.normalize(
                preload.get_floating_ip(
                    port.vm.vm_type, port.network.network_role, ip.ip_version, ip.param
                ),
                ip.param,
            )
            ips.append(value)

    def add_fixed_ips(
        self, network_template: dict, port: Port, preload: AbstractPreloadInstance
    ):
        items = network_template["network-information-items"][
            "network-information-item"
        ]
        ipv4s = next(item for item in items if item["ip-version"] == "4")
        ipv6s = next(item for item in items if item["ip-version"] == "6")
        if port.uses_dhcp:
            ipv4s["use-dhcp"] = "Y"
            ipv6s["use-dhcp"] = "Y"
        for index, ip in port.fixed_ips_with_index:
            target = ipv4s if ip.ip_version == 4 else ipv6s
            ips = target["network-ips"]["network-ip"]
            if ip.param not in ips:
                ips.append(
                    self.normalize(
                        preload.get_fixed_ip(
                            port.vm.vm_type,
                            port.network.network_role,
                            ip.ip_version,
                            index,
                            ip.param,
                        ),
                        ip.param,
                        index=index
                    )
                )
            target["ip-count"] += 1

    def _add_vms(
        self, template: Mapping, preload: AbstractPreloadInstance, vnf_module: VnfModule
    ):
        vms = template["input"]["preload-vf-module-topology-information"][
            "vf-module-topology"
        ]["vf-module-assignments"]["vms"]["vm"]
        for vm in vnf_module.virtual_machine_types:
            vm_template = get_json_template(DATA_DIR, "vm")
            vms.append(vm_template)
            vm_template["vm-type"] = vm.vm_type
            for i, param in enumerate(sorted(vm.names)):
                name = preload.get_vm_name(vm.vm_type, i, param)
                value = self.normalize(name, param, index=i)
                vm_template["vm-names"]["vm-name"].append(value)
            vm_template["vm-count"] = vm.vm_count
            vm_networks = vm_template["vm-networks"]["vm-network"]
            for port in vm.ports:
                role = port.network.network_role
                network_template = get_or_create_network_template(role, vm_networks)
                network_template["network-role"] = role
                network_template["network-role-tag"] = role
                self.add_fixed_ips(network_template, port, preload)
                self.add_floating_ips(network_template, port, preload)

    def _add_parameters(
        self, template: Mapping, preload: AbstractPreloadInstance, vnf_module: VnfModule
    ):
        params = [
            {
                "name": key,
                "value": self.normalize(preload.get_vnf_parameter(key, value), key),
            }
            for key, value in vnf_module.preload_parameters.items()
        ]
        for key, value in preload.get_additional_parameters().items():
            params.append(
                {
                    "name": key,
                    "value": value,
                }
            )

        template["input"]["preload-vf-module-topology-information"][
            "vf-module-topology"
        ]["vf-module-parameters"]["param"].extend(params)
