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

DATA_DIR = "{}/grapi_data".format(os.path.dirname(os.path.abspath(__file__)))


class GrApiPreload:
    def __init__(self):
        self.vms = []
        self.parameters = []
        self._preload = {}
        self.init_preload()

    @property
    def preload(self):
        preload = self._preload

        for vm in self.vms:
            preload["input"]["preload-vf-module-topology-information"][
                "vf-module-topology"
            ]["vf-module-assignments"]["vms"]["vm"].append(vm)

        for param in self.parameters:
            preload["input"]["preload-vf-module-topology-information"][
                "vf-module-topology"
            ]["vf-module-parameters"]["param"].append(param)

        return preload

    def init_preload(self):
        self._preload = get_json_template("preload_template")

    def add_availability_zones(self, *zones):
        availability_zones = self._preload["input"][
            "preload-vf-module-topology-information"
        ]["vnf-resource-assignments"]["availability-zones"]["availability-zone"]

        for zone in zones:
            if zone in availability_zones:
                continue
            self._preload["input"]["preload-vf-module-topology-information"][
                "vnf-resource-assignments"
            ]["availability-zones"]["availability-zone"].append(zone)

    def add_vnf_network(self, network_role, network_name=""):
        networks = self._preload["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["vnf-networks"]["vnf-network"]
        for network in networks:
            if network["network-role"] == network_role:
                # print("network {} already added to preload")
                return

        jdata = get_json_template("vnf-network")

        jdata["network-role"] = network_role
        jdata["network-name"] = network_name

        self._preload["input"]["preload-vf-module-topology-information"][
            "vnf-resource-assignments"
        ]["vnf-networks"]["vnf-network"].append(jdata)

    def add_vm_type(self, vm_type, vm_name):
        vm_obj, __ = self._get_vm_type_object(vm_type)

        if not vm_obj:
            jdata = get_json_template("vm")
            jdata["vm-type"] = vm_type
            jdata["vm-names"]["vm-name"].append(vm_name)
            jdata["vm-count"] = 1
            self.vms.append(jdata)
        else:
            vm_obj["vm-names"]["vm-name"].append(vm_name)
            vm_obj["vm-count"] = vm_obj["vm-count"] + 1
            self.vms[__] = vm_obj

    def add_network_role(self, vm_type, network_role):
        vm_obj, vm_type_index = self._get_vm_type_object(vm_type)

        if not vm_obj:
            return

        network_obj, network_role_index = self._get_network_role_object(
            network_role, vm_obj=vm_obj
        )

        if network_obj:
            return

        jdata = get_json_template("vm-network")

        jdata["network-role"] = network_role

        self._create_or_update_nr_object(
            vm_type, jdata, index=network_role_index, new=True
        )

    def add_parameter(self, parameter_name, parameter_value=""):
        jdata = get_json_template("vf-module-parameter")

        jdata["name"] = parameter_name
        jdata["value"] = parameter_value

        self.parameters.append(jdata)

    def add_vm_ipv4(self, vm_type, network_role, *ips):
        self._add_vm_ips(vm_type, network_role, "4", ips)

    def add_vm_ipv6(self, vm_type, network_role, *ips):
        self._add_vm_ips(vm_type, network_role, "6", ips)

    def add_mac_address(self, vm_type, network_role, mac_address):
        nr_obj, nr_index = self._get_network_role_object(network_role, vm_type=vm_type)

        if not nr_obj:
            # print("No data found for {} {}".format(vm_type, network_role))
            return

        nr_obj["mac-addresses"]["mac-address"].append(mac_address)

        self._create_or_update_nr_object(vm_type, nr_obj, index=nr_index, new=False)

    def add_interface_route_prefixes(self, vm_type, network_role, prefix):
        nr_obj, nr_index = self._get_network_role_object(network_role, vm_type=vm_type)

        if not nr_obj:
            return

        nr_obj["interface-route-prefixes"]["interface-route-prefix"].append(prefix)

        self._create_or_update_nr_object(vm_type, nr_obj, index=nr_index, new=False)

    def add_floating_ip(self, vm_type, network_role, ipv4=None, ipv6=None):
        nr_obj, nr_index = self._get_network_role_object(network_role, vm_type=vm_type)

        if not nr_obj:
            return

        if ipv4:
            nr_obj["floating-ips"]["floating-ip-v4"] = [ipv4]

        if ipv6:
            nr_obj["floating-ips"]["floating-ip-v6"] = [ipv6]

        self._create_or_update_nr_object(vm_type, nr_obj, index=nr_index, new=False)

    def _add_vm_ips(self, vm_type, network_role, version, ips):
        network_obj, network_index = self._get_network_role_object(
            network_role, vm_type=vm_type
        )

        if not network_obj:
            return

        if version == "4":
            idx = 0
        else:
            idx = 1

        count = network_obj["network-information-items"]["network-information-item"][
            idx
        ]["ip-count"]
        for ip in ips:
            network_obj["network-information-items"]["network-information-item"][idx][
                "network-ips"
            ]["network-ip"].append(ip)
            count += 1

        network_obj["network-information-items"]["network-information-item"][idx][
            "ip-count"
        ] = count

        self._create_or_update_nr_object(
            vm_type, network_obj, index=network_index, new=False
        )

    def _create_or_update_nr_object(
        self, vm_type, network_object, index=None, new=False
    ):
        vm_obj, vm_index = self._get_vm_type_object(vm_type)

        if not vm_obj:
            return

        if new:
            vm_obj["vm-networks"]["vm-network"].append(network_object)
        elif index:
            vm_obj["vm-networks"]["vm-network"][index] = network_object

        self.vms[vm_index] = vm_obj

    def _get_vm_type_object(self, vm_type):
        vm_obj = None
        vm_index = 0
        for vm in self.vms:
            if vm.get("vm-type") == vm_type:
                vm_obj = vm
                break
            vm_index += 1

        return vm_obj, vm_index

    def _get_network_role_object(self, network_role, vm_obj=None, vm_type=None):
        if vm_obj is None:
            if vm_type is None:
                return None
            else:
                vm_obj, __ = self._get_vm_type_object(vm_type)

        vm_networks = vm_obj.get("vm-networks")

        network_obj = None
        network_index = 0
        for network in vm_networks.get("vm-network"):
            if network.get("network-role") == network_role:
                network_obj = network
                break
            network_index += 1

        return network_obj, network_index


def get_json_template(template_name):
    try:
        with open("{}/{}.json".format(DATA_DIR, template_name, "r")) as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return {}
