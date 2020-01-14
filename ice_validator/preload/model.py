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
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from itertools import chain
from typing import Tuple, List

from tests.helpers import (
    get_param,
    get_environment_pair,
    prop_iterator,
    is_base_module,
    remove,
)
from tests.parametrizers import parametrize_heat_templates
from tests.structures import NeutronPortProcessor, Heat
from tests.test_environment_file_parameters import get_preload_excluded_parameters
from tests.utils import nested_dict
from tests.utils.vm_types import get_vm_type_for_nova_server

from tests.test_environment_file_parameters import ENV_PARAMETER_SPEC

CHANGE = "CHANGEME"


# This is only used to fake out parametrizers
class DummyMetafunc:
    def __init__(self, config):
        self.inputs = {}
        self.config = config

    def parametrize(self, name, file_list):
        self.inputs[name] = file_list


def get_heat_templates(config):
    """
    Returns the Heat template paths discovered by the pytest parameterizers
    :param config: pytest config
    :return: list of heat template paths
    """
    meta = DummyMetafunc(config)
    parametrize_heat_templates(meta)
    heat_templates = meta.inputs.get("heat_templates", [])
    if isinstance(heat_templates, list) and len(heat_templates) > 0:
        heat_templates = heat_templates[0]
    else:
        return
    return heat_templates


class FilterBaseOutputs(ABC):
    """
    Invoked to remove parameters in an object that appear in the base module.
    Base output parameters can be passed to incremental modules
    so they do not need to be defined in a preload.  This method can be
    invoked on a module to pre-filter the parameters before a preload is
    created.

    The method should remove the parameters that exist in the base module from
    both itself and any sub-objects.
    """

    @abstractmethod
    def filter_output_params(self, base_outputs):
        raise NotImplementedError()


class IpParam:
    def __init__(self, ip_addr_param, port):
        self.param = ip_addr_param or ""
        self.port = port

    @property
    def ip_version(self):
        return 6 if "_v6_" in self.param else 4

    def __hash__(self):
        return hash(self.param)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return "{}(v{})".format(self.param, self.ip_version)

    def __repr(self):
        return str(self)


class Network(FilterBaseOutputs):
    def __init__(self, role, name_param):
        self.network_role = role
        self.name_param = name_param
        self.subnet_params = set()

    def filter_output_params(self, base_outputs):
        self.subnet_params = remove(
            self.subnet_params, base_outputs, key=lambda s: s.param_name
        )

    def __hash__(self):
        return hash(self.network_role)

    def __eq__(self, other):
        return hash(self) == hash(other)


class Subnet:
    def __init__(self, param_name: str):
        self.param_name = param_name

    @property
    def ip_version(self):
        return 6 if "_v6_" in self.param_name else 4

    def __hash__(self):
        return hash(self.param_name)

    def __eq__(self, other):
        return hash(self) == hash(other)


class Port(FilterBaseOutputs):
    def __init__(self, vm, network):
        self.vm = vm
        self.network = network
        self.fixed_ips = []
        self.floating_ips = set()
        self.uses_dhcp = True

    def add_ips(self, props):
        props = props.get("properties") or props
        for fixed_ip in props.get("fixed_ips") or []:
            if not isinstance(fixed_ip, dict):
                continue
            ip_address = get_param(fixed_ip.get("ip_address"))
            subnet = get_param(fixed_ip.get("subnet") or fixed_ip.get("subnet_id"))
            if ip_address:
                self.uses_dhcp = False
                self.fixed_ips.append(IpParam(ip_address, self))
            if subnet:
                self.network.subnet_params.add(Subnet(subnet))
        for ip in prop_iterator(props, "allowed_address_pairs", "ip_address"):
            param = get_param(ip) if ip else ""
            if param:
                self.floating_ips.add(IpParam(param, self))

    @property
    def ipv6_fixed_ips(self):
        return list(
            sorted(
                (ip for ip in self.fixed_ips if ip.ip_version == 6),
                key=lambda ip: ip.param,
            )
        )

    @property
    def ipv4_fixed_ips(self):
        return list(
            sorted(
                (ip for ip in self.fixed_ips if ip.ip_version == 4),
                key=lambda ip: ip.param,
            )
        )

    @property
    def fixed_ips_with_index(self) -> List[Tuple[int, IpParam]]:
        ipv4s = enumerate(self.ipv4_fixed_ips)
        ipv6s = enumerate(self.ipv6_fixed_ips)
        return list(chain(ipv4s, ipv6s))

    def filter_output_params(self, base_outputs):
        self.fixed_ips = remove(self.fixed_ips, base_outputs, key=lambda ip: ip.param)
        self.floating_ips = remove(
            self.floating_ips, base_outputs, key=lambda ip: ip.param
        )


class VirtualMachineType(FilterBaseOutputs):
    def __init__(self, vm_type, vnf_module):
        self.vm_type = vm_type
        self.names = []
        self.ports = []
        self.vm_count = 0
        self.vnf_module = vnf_module

    def filter_output_params(self, base_outputs):
        self.names = remove(self.names, base_outputs)
        for port in self.ports:
            port.filter_output_params(base_outputs)

    @property
    def networks(self):
        return {port.network for port in self.ports}

    @property
    def floating_ips(self):
        for port in self.ports:
            for ip in port.floating_ips:
                yield ip

    @property
    def fixed_ips(self):
        for port in self.ports:
            for ip in port.fixed_ips:
                yield ip

    def update_ports(self, network, props):
        port = self.get_or_create_port(network)
        port.add_ips(props)

    def get_or_create_port(self, network):
        for port in self.ports:
            if port.network == network:
                return port
        port = Port(self, network)
        self.ports.append(port)
        return port


class Vnf:
    def __init__(self, templates, config=None):
        self.modules = [VnfModule(t, self, config) for t in templates]
        self.uses_contrail = self._uses_contrail()
        self.config = config
        self.base_module = next(
            (mod for mod in self.modules if mod.is_base_module), None
        )
        self.incremental_modules = [m for m in self.modules if not m.is_base_module]

    def _uses_contrail(self):
        for mod in self.modules:
            resources = mod.heat.get_all_resources()
            types = (r.get("type", "") for r in resources.values())
            if any(t.startswith("OS::ContrailV2") for t in types):
                return True
        return False

    @property
    def base_output_params(self):
        return self.base_module.heat.outputs if self.base_module else {}

    def filter_base_outputs(self):
        non_base_modules = (m for m in self.modules if not m.is_base_module)
        for mod in non_base_modules:
            mod.filter_output_params(self.base_output_params)


def env_path(heat_path):
    """
    Create the path to the env file for the give heat path.
    :param heat_path: path to heat file
    :return: path to env file (assumes it is present and named correctly)
    """
    base_path = os.path.splitext(heat_path)[0]
    env_path = "{}.env".format(base_path)
    return env_path if os.path.exists(env_path) else None


class VnfModule(FilterBaseOutputs):
    def __init__(self, template_file, vnf, config):
        self.vnf = vnf
        self.config = config
        self.vnf_name = os.path.splitext(os.path.basename(template_file))[0]
        self.template_file = template_file
        self.heat = Heat(filepath=template_file, envpath=env_path(template_file))
        env_pair = get_environment_pair(self.template_file)
        env_yaml = env_pair.get("eyml") if env_pair else {}
        self.parameters = {key: "" for key in self.heat.parameters}
        self.parameters.update(env_yaml.get("parameters") or {})
        # Filter out any parameters passed from the volume module's outputs
        self.parameters = {
            key: value
            for key, value in self.parameters.items()
            if key not in self.volume_module_outputs
        }
        self.networks = []
        self.virtual_machine_types = self._create_vm_types()
        self._add_networks()
        self.outputs_filtered = False

    @property
    def volume_module_outputs(self):
        heat_dir = os.path.dirname(self.template_file)
        heat_filename = os.path.basename(self.template_file)
        basename, ext = os.path.splitext(heat_filename)
        volume_template_name = "{}_volume{}".format(basename, ext)
        volume_path = os.path.join(heat_dir, volume_template_name)
        if os.path.exists(volume_path):
            volume_mod = Heat(filepath=volume_path)
            return volume_mod.outputs
        else:
            return {}

    def filter_output_params(self, base_outputs):
        for vm in self.virtual_machine_types:
            vm.filter_output_params(base_outputs)
        for network in self.networks:
            network.filter_output_params(base_outputs)
        self.parameters = {
            k: v for k, v in self.parameters.items() if k not in base_outputs
        }
        self.networks = [
            network
            for network in self.networks
            if network.name_param not in base_outputs or network.subnet_params
        ]
        self.outputs_filtered = True

    def _create_vm_types(self):
        servers = self.heat.get_resource_by_type("OS::Nova::Server", all_resources=True)
        vm_types = {}
        for _, props in yield_by_count(servers):
            vm_type = get_vm_type_for_nova_server(props)
            vm = vm_types.setdefault(vm_type, VirtualMachineType(vm_type, self))
            vm.vm_count += 1
            name = nested_dict.get(props, "properties", "name", default={})
            vm_name = get_param(name) if name else ""
            vm.names.append(vm_name)
        return list(vm_types.values())

    def _add_networks(self):
        ports = self.heat.get_resource_by_type("OS::Neutron::Port", all_resources=True)
        for rid, props in yield_by_count(ports):
            resource_type, port_match = NeutronPortProcessor.get_rid_match_tuple(rid)
            if resource_type != "external":
                continue
            network_role = port_match.group("network_role")
            vm = self._get_vm_type(port_match.group("vm_type"))
            network = self._get_network(network_role, props)
            vm.update_ports(network, props)

    @property
    def is_base_module(self):
        return is_base_module(self.template_file)

    @property
    def availability_zones(self):
        """Returns a list of all availability zone parameters found in the template"""
        return sorted(
            p for p in self.heat.parameters if p.startswith("availability_zone")
        )

    @property
    def label(self):
        """
        Label for the VF module that will appear in the CSAR
        """
        return self.vnf_name

    @property
    def env_specs(self):
        """Return available Environment Spec definitions"""
        return [ENV_PARAMETER_SPEC] if not self.config else self.config.env_specs

    @property
    def platform_provided_params(self):
        result = set()
        for spec in self.env_specs:
            for props in spec["PLATFORM PROVIDED"]:
                result.add(props["property"][-1])
        return result

    @property
    def env_template(self):
        """
        Returns a a template .env file that can be completed to enable
        preload generation.
        """
        params = OrderedDict()
        params["vnf-type"] = CHANGE
        params["vf-module-model-name"] = CHANGE
        params["vf_module_name"] = CHANGE
        for az in self.availability_zones:
            params[az] = CHANGE
        for network in self.networks:
            params[network.name_param] = CHANGE
            for param in set(s.param_name for s in network.subnet_params):
                params[param] = CHANGE
        for vm in self.virtual_machine_types:
            for name in set(vm.names):
                params[name] = CHANGE
            for ip in vm.floating_ips:
                params[ip.param] = CHANGE
            for ip in vm.fixed_ips:
                params[ip.param] = CHANGE
        excluded = get_preload_excluded_parameters(
            self.template_file, persistent_only=True
        )
        excluded.update(self.platform_provided_params)
        for name, value in self.parameters.items():
            if name in excluded:
                continue
            params[name] = value if value else CHANGE
        return {"parameters": params}

    @property
    def preload_parameters(self):
        """
        Subset of parameters from the env file that can be overridden in
        tag values. Per VNF Heat Guidelines, specific parameters such as
        flavor, image, etc. must not be overridden so they are excluded.

        :return: dict of parameters suitable for the preload
        """
        excluded = get_preload_excluded_parameters(self.template_file)
        excluded.update(self.platform_provided_params)
        params = {k: v for k, v in self.parameters.items() if k not in excluded}
        return params

    def _get_vm_type(self, vm_type):
        for vm in self.virtual_machine_types:
            if vm_type.lower() == vm.vm_type.lower():
                return vm
        raise RuntimeError("Encountered unknown VM type: {}".format(vm_type))

    def _get_network(self, network_role, props):
        network_prop = nested_dict.get(props, "properties", "network") or {}
        name_param = get_param(network_prop) if network_prop else ""
        for network in self.networks:
            if network.network_role.lower() == network_role.lower():
                return network
        new_network = Network(network_role, name_param)
        self.networks.append(new_network)
        return new_network

    def __str__(self):
        return "VNF Module ({})".format(os.path.basename(self.template_file))

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.vnf_name)

    def __eq__(self, other):
        return hash(self) == hash(other)


def yield_by_count(sequence):
    """
    Iterates through sequence and yields each item according to its __count__
    attribute.  If an item has a __count__ of it will be returned 3 times
    before advancing to the next item in the sequence.

    :param sequence: sequence of dicts (must contain __count__)
    :returns:        generator of tuple key, value pairs
    """
    for key, value in sequence.items():
        for i in range(value["__count__"]):
            yield (key, value)
