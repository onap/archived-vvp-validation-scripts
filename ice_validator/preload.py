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
import importlib
import inspect
import json
import os
import pkgutil
import shutil
from abc import ABC, abstractmethod
from itertools import chain
from typing import Set

from tests.helpers import (
    get_param,
    get_environment_pair,
    prop_iterator,
    get_output_dir,
    is_base_module,
)
from tests.parametrizers import parametrize_heat_templates
from tests.structures import NeutronPortProcessor, Heat
from tests.utils import nested_dict
from tests.utils.vm_types import get_vm_type_for_nova_server


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


def get_json_template(template_dir, template_name):
    template_name = template_name + ".json"
    with open(os.path.join(template_dir, template_name)) as f:
        return json.loads(f.read())


def remove(sequence, exclude, key=None):
    """
    Remove a copy of sequence that items occur in exclude.

    :param sequence: sequence of objects
    :param exclude:  objects to excluded (must support ``in`` check)
    :param key:      optional function to extract key from item in sequence
    :return:         list of items not in the excluded
    """
    key_func = key if key else lambda x: x
    result = (s for s in sequence if key_func(s) not in exclude)
    return set(result) if isinstance(sequence, Set) else list(result)


def get_or_create_template(template_dir, key, value, sequence, template_name):
    """
    Search a sequence of dicts where a given key matches value.  If
    found, then it returns that item.  If not, then it loads the
    template identified by template_name, adds it ot the sequence, and
    returns the template
    """
    for item in sequence:
        if item[key] == value:
            return item
    new_template = get_json_template(template_dir, template_name)
    sequence.append(new_template)
    return new_template


def replace(s):
    return "VALUE FOR: {}".format(s)


class AbstractPreloadGenerator(ABC):
    """
    All preload generators must inherit from this class and implement the
    abstract methods.

    Preload generators are automatically discovered at runtime via a plugin
    architecture.  The system path is scanned looking for modules with the name
    preload_*, then all non-abstract classes that inherit from AbstractPreloadGenerator
    are registered as preload plugins

    Attributes:
        :param vnf:             Instance of Vnf that contains the preload data
        :param base_output_dir: Base directory to house the preloads.  All preloads
                                must be written to a subdirectory under this directory
    """

    def __init__(self, vnf, base_output_dir):
        self.vnf = vnf
        self.base_output_dir = base_output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @classmethod
    @abstractmethod
    def format_name(cls):
        """
        String name to identify the format (ex: VN-API, GR-API)
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def output_sub_dir(cls):
        """
        String sub-directory name that will appear under ``base_output_dir``
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def supports_output_passing(cls):
        """
        Some preload methods allow automatically mapping output parameters in the
        base module to the input parameter of other modules.  This means these
        that the incremental modules do not need these base module outputs in their
        preloads.

        At this time, VNF-API does not support output parameter passing, but
        GR-API does.

        If this is true, then the generator will call Vnf#filter_output_params
        after the preload module for the base module has been created
        """
        raise NotImplementedError()

    @abstractmethod
    def generate_module(self, module):
        """
        Create the preloads and write them to ``self.output_dir``.  This
        method is responsible for generating the content of the preload and
        writing the file to disk.
        """
        raise NotImplementedError()

    @property
    def output_dir(self):
        return os.path.join(self.base_output_dir, self.output_sub_dir())

    def generate(self):
        # handle the base module first
        print("\nGenerating {} preloads".format(self.format_name()))
        self.generate_module(self.vnf.base_module)
        print(
            "... generated template for {}".format(self.vnf.base_module)
        )
        if self.supports_output_passing():
            self.vnf.filter_base_outputs()
        for mod in self.vnf.incremental_modules:
            self.generate_module(mod)
            print("... generated for {}".format(mod))


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
        return 6 if "v6" in self.param else 4

    def __hash__(self):
        return hash(self.param)

    def __eq__(self, other):
        return hash(self) == hash(other)


class Network(FilterBaseOutputs):
    def __init__(self, role, name_param):
        self.network_role = role
        self.name_param = name_param
        self.subnet_params = set()

    def filter_output_params(self, base_outputs):
        self.subnet_params = remove(self.subnet_params, base_outputs)

    def __hash__(self):
        return hash(self.network_role)

    def __eq__(self, other):
        return hash(self) == hash(other)


class Port(FilterBaseOutputs):
    def __init__(self, vm, network, props):
        self.vm = vm
        self.network = network
        self.fixed_ips = set()
        self.floating_ips = set()
        self.props = props.get("properties") or props
        self.uses_dhcp = False
        self._init()

    def _init(self):
        uses_dhcp = True
        for fixed_ip in self.props.get("fixed_ips") or []:
            if not isinstance(fixed_ip, dict):
                continue
            ip_address = get_param(fixed_ip.get("ip_address"))
            subnet = get_param(fixed_ip.get("subnet") or fixed_ip.get("subnet_id"))
            if ip_address:
                uses_dhcp = False
                self.fixed_ips.add(IpParam(ip_address, self))
            if subnet:
                self.network.subnet_params.add(subnet)
        for ip in prop_iterator(self.props, "allowed_address_pairs", "ip_address"):
            uses_dhcp = False
            param = get_param(ip) if ip else ""
            if param:
                self.floating_ips.add(IpParam(param, self))
        self.uses_dhcp = uses_dhcp

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


class Vnf:
    def __init__(self, templates):
        self.modules = [VnfModule(t, self) for t in templates]
        self.uses_contrail = self._uses_contrail()
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
        return self.base_module.heat.outputs

    def filter_base_outputs(self):
        non_base_modules = (m for m in self.modules if not m.is_base_module)
        for mod in non_base_modules:
            mod.filter_output_params(self.base_output_params)


class VnfModule(FilterBaseOutputs):
    def __init__(self, template_file, vnf):
        self.vnf = vnf
        self.vnf_name = os.path.splitext(os.path.basename(template_file))[0]
        self.template_file = template_file
        self.heat = Heat(template_file)
        self.networks = []
        self.virtual_machine_types = self._create_vm_types()
        self._add_networks()
        env_pair = get_environment_pair(self.template_file)
        env_yaml = env_pair.get("eyml") if env_pair else {}
        self.parameters = env_yaml.get("parameters") or {}
        self.outputs_filtered = False

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
        for server, props in servers.items():
            vm_type = get_vm_type_for_nova_server(props)
            vm = vm_types.setdefault(vm_type, VirtualMachineType(vm_type, self))
            vm.vm_count += 1
            name = nested_dict.get(props, "properties", "name", default={})
            vm_name = get_param(name) if name else ""
            vm.names.append(vm_name)
        return list(vm_types.values())

    def _add_networks(self):
        ports = self.heat.get_resource_by_type("OS::Neutron::Port", all_resources=True)
        for port, props in ports.items():
            resource_type, port_match = NeutronPortProcessor.get_rid_match_tuple(port)
            if resource_type != "external":
                continue
            network_role = port_match.group("network_role")
            vm = self._get_vm_type(port_match.group("vm_type"))
            network = self._get_network(network_role, props)
            port = Port(vm, network, props)
            vm.ports.append(port)

    @property
    def is_base_module(self):
        return is_base_module(self.template_file)

    @property
    def availability_zones(self):
        """Returns a list of all availability zone parameters found in the template"""
        return sorted(
            p for p in self.heat.parameters if p.startswith("availability_zone")
        )

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


def create_preloads(config, exitstatus):
    """
    Create preloads in every format that can be discovered by get_generator_plugins
    """
    if config.getoption("self_test"):
        return
    print("+===================================================================+")
    print("|                      Preload Template Generation                  |")
    print("+===================================================================+")

    preload_dir = os.path.join(get_output_dir(config), "preloads")
    if os.path.exists(preload_dir):
        shutil.rmtree(preload_dir)
    heat_templates = get_heat_templates(config)
    vnf = None
    for gen_class in get_generator_plugins():
        vnf = Vnf(heat_templates)
        generator = gen_class(vnf, preload_dir)
        generator.generate()
    if vnf and vnf.uses_contrail:
        print(
            "\nWARNING: Preload template generation does not support Contrail\n"
            "at this time, but Contrail resources were detected. The preload \n"
            "template may be incomplete."
        )
    if exitstatus != 0:
        print(
            "\nWARNING: Heat violations detected. Preload templates may be\n"
            "incomplete."
        )


def is_preload_generator(class_):
    """
    Returns True if the class is an implementation of AbstractPreloadGenerator
    """
    return (
        inspect.isclass(class_)
        and not inspect.isabstract(class_)
        and issubclass(class_, AbstractPreloadGenerator)
    )


def get_generator_plugins():
    """
    Scan the system path for modules that are preload plugins and discover
    and return the classes that implement AbstractPreloadGenerator in those
    modules
    """
    preload_plugins = (
        importlib.import_module(name)
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith("preload_")
    )
    members = chain.from_iterable(
        inspect.getmembers(mod, is_preload_generator) for mod in preload_plugins
    )
    return [m[1] for m in members]
