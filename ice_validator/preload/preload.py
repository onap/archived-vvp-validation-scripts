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

import os
import json

from preload.grapi_preload import GrApiPreload
from preload.vnfapi_preload import VnfApiPreload

from tests.helpers import get_param, prop_iterator, get_environment_pair
from tests.utils.vm_types import get_vm_type_for_nova_server
from tests.structures import Heat, NeutronPortProcessor
from tests.utils import nested_dict


class Preload:
    def __init__(self, vnf_name, vnf_type, template_file, output_directory, preload_format="vnfapi"):
        self.vnf_name = vnf_name
        self.vnf_type = vnf_type
        self.template_file = template_file
        self.output_directory = output_directory
        self.preload_format = preload_format

        if preload_format == "vnfapi":
            VNFPreload = VnfApiPreload
        else:
            VNFPreload = GrApiPreload

        self._json_preload = VNFPreload(vnf_name, vnf_type)

        self.init_json_preload()

    def init_json_preload(self):
        self.create_vm_section()
        self.create_networks_section()
        self.create_availability_zones_section()
        self.create_parameters_section()

    @property
    def preload(self):
        return self._json_preload.preload

    def print(self):
        print(json.dumps(self.preload, indent=4))

    # TODO
    # Add Contrail Support
    def create_networks_section(self):
        heat = Heat(self.template_file)

        # adding nested files to resource collection
        heat.resources = (heat.get_all_resources(os.path.dirname(self.template_file)))

        ports = heat.get_resource_by_type("OS::Neutron::Port")
        for port, props in ports.items():
            resource_type, port_match = NeutronPortProcessor.get_rid_match_tuple(port)
            if resource_type != "external":
                continue
            vm_type = port_match.group("vm_type")
            network_role = port_match.group("network_role")
            self._json_preload.add_network_role(vm_type, network_role)

            for ip in prop_iterator(props, "fixed_ips", "ip_address"):
                param = get_param(ip) if ip else ""
                if "v6" in ip:
                    self._json_preload.add_vm_ipv6(vm_type, network_role, param)
                else:
                    self._json_preload.add_vm_ipv4(vm_type, network_role, param)

            for ip in prop_iterator(props, "allowed_address_pairs", "ip_address"):
                param = get_param(ip) if ip else ""
                if "v6" in ip:
                    self._json_preload.add_floating_ip(vm_type, network_role, ipv6=param)
                else:
                    self._json_preload.add_floating_ip(vm_type, network_role, ipv4=param)

            network = nested_dict.get(props, "properties", "network", default={})
            param = get_param(network) if network else ""

            self._json_preload.add_vnf_network(network_role, network_name=param)

    def create_availability_zones_section(self):
        heat = Heat(self.template_file)

        for param, value in heat.parameters.items():
            if param.startswith("availability_zone"):
                self._json_preload.add_availability_zones(param)

    def create_parameters_section(self):
        env_pair = get_environment_pair(self.template_file)
        env_yaml = env_pair.get("eyml") if env_pair else {}

        parameters = env_yaml.get("parameters", {})

        if parameters:
            for param, value in parameters.items():
                self._json_preload.add_parameter(param, parameter_value=value)

    def create_vm_section(self):
        heat = Heat(self.template_file)

        # adding nested files to resource collection
        heat.resources = (heat.get_all_resources(os.path.dirname(self.template_file)))

        servers = heat.get_resource_by_type("OS::Nova::Server")

        for server, props in servers.items():
            vm_type = get_vm_type_for_nova_server(props)
            name = nested_dict.get(props, "properties", "name", default={})
            vm_name = get_param(name) if name else ""
            self._json_preload.add_vm_type(vm_type, vm_name)

    def write_preload(self):
        print("creating preload for {}".format(self.vnf_name))
        outfile = "{}/{}.json".format(self.output_directory, self.vnf_name)
        with open(outfile, "w") as f:
            json.dump(self.preload, f, indent=4)


def main(template_file, output, preload_format="vnfapi"):

    # TODO
    # For now, the vnf-name and vnf-type are derived from the filesystem path
    # and file name.
    module_name = os.path.splitext(os.path.basename(template_file))[0]
    template_dir = os.path.basename(os.path.dirname(os.path.abspath(template_file)))

    preload = Preload(module_name, template_dir, template_file, output, preload_format=preload_format)
    preload.write_preload()
