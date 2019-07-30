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
""" environment file structure
"""
import os

import re
import pytest
from tests.helpers import (
    prop_iterator,
    get_param,
    get_environment_pair,
    validates,
    find_environment_file,
    categories,
)
from tests.structures import Heat
from tests.utils.nested_files import file_is_a_nested_template


# Whats persistent mean? It means it goes in env.
# When adding an additional case, note the ","
# at the end of a property to make it a tuple.
ENV_PARAMETER_SPEC = {
    "PLATFORM PROVIDED": [
        {"property": ("vnf_id",), "persistent": False, "kwargs": {}},
        {"property": ("vnf_name",), "persistent": False, "kwargs": {}},
        {"property": ("vf_module_id",), "persistent": False, "kwargs": {}},
        {"property": ("vf_module_index",), "persistent": False, "kwargs": {}},
        {"property": ("vf_module_name",), "persistent": False, "kwargs": {}},
        {"property": ("workload_context",), "persistent": False, "kwargs": {}},
        {"property": ("environment_context",), "persistent": False, "kwargs": {}},
        {"property": (r"^(.+?)_net_fqdn$",), "persistent": False, "kwargs": {}},
    ],
    "ALL": [{"property": ("name",), "persistent": False, "kwargs": {}}],
    "OS::Nova::Server": [
        {"property": ("image",), "persistent": True, "kwargs": {}},
        {"property": ("flavor",), "persistent": True, "kwargs": {}},
        {"property": ("availability_zone",), "persistent": False, "kwargs": {}},
    ],
    "OS::Neutron::Port": [
        {"property": ("network",), "persistent": False, "kwargs": {}},
        {
            "property": ("fixed_ips", "ip_address"),
            "persistent": False,
            "network_type": "external",
            "kwargs": {"exclude_parameter": re.compile(r"^(.+?)_int_(.+?)$")},
        },
        {
            "property": ("fixed_ips", "ip_address"),
            "persistent": True,
            "network_type": "internal",
            "kwargs": {"exclude_parameter": re.compile(r"^((?!_int_).)*$")},
        },
        {"property": ("fixed_ips", "subnet"), "persistent": False, "kwargs": {}},
        {
            "property": ("fixed_ips", "allowed_address_pairs"),
            "persistent": False,
            "network_type": "external",
            "kwargs": {"exclude_parameter": re.compile(r"^(.+?)_int_(.+?)$")},
        },
        {
            "property": ("fixed_ips", "allowed_address_pairs"),
            "persistent": True,
            "network_type": "internal",
            "kwargs": {"exclude_parameter": re.compile(r"^((?!_int_).)*$")},
        },
    ],
    "OS::ContrailV2::InterfaceRouteTable": [
        {
            "property": (
                "interface_route_table_routes",
                "interface_route_table_routes_route",
            ),
            "persistent": False,
            "kwargs": {},
        }
    ],
    "OS::Heat::ResourceGroup": [
        {
            "property": ("count",),
            "persistent": True,
            "kwargs": {
                "exclude_resource": re.compile(
                    r"^(.+?)_subint_(.+?)_port_(.+?)_subinterfaces$"
                )
            },
        }
    ],
    "OS::ContrailV2::InstanceIp": [
        {
            "property": ("instance_ip_address",),
            "persistent": False,
            "network_type": "external",
            "kwargs": {"exclude_resource": re.compile(r"^.*_int_.*$")},
        },
        {
            "property": ("instance_ip_address",),
            "persistent": True,
            "network_type": "internal",
            "kwargs": {"exclude_resource": re.compile(r"(?!.*_int_.*)")},
        },
        {
            "property": ("subnet_uuid",),
            "persistent": False,
            "network_type": "internal",
            "kwargs": {"exclude_resource": re.compile(r"(?!.*_int_.*)")},
        },
    ],
    "OS::ContrailV2::VirtualMachineInterface": [
        {
            "property": (
                "virtual_machine_interface_allowed_address_pairs",
                "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
                "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip",
                "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip_ip_prefix",
            ),
            "persistent": False,
            "network_type": "external",
            "kwargs": {"exclude_resource": re.compile(r"(?!.*_int_.*)")},
        }
    ],
}


def run_test_parameter(yaml_file, resource_type, *prop, **kwargs):
    template_parameters = []
    invalid_parameters = []
    param_spec = {}
    parameter_spec = ENV_PARAMETER_SPEC.get(
        resource_type
    )  # matching spec dict on resource type
    for spec in parameter_spec:
        # iterating through spec dict and trying to match on property
        if spec.get("property") == prop:
            yep = True
            for (
                k,
                v,
            ) in (
                kwargs.items()
            ):  # now matching on additional kwargs passed in from test (i.e. network_type)
                if not spec.get(k) or spec.get(k) != v:
                    yep = False
            if yep:
                param_spec = spec
                if resource_type == "PLATFORM PROVIDED":
                    if file_is_a_nested_template(yaml_file):
                        pytest.skip(
                            "Not checking nested files for PLATFORM PROVIDED params"
                        )
                    template_parameters.append(
                        {"resource": "", "param": param_spec.get("property")[0]}
                    )
                else:
                    all_resources = False
                    if resource_type == "ALL":
                        all_resources = True
                    template_parameters = get_template_parameters(
                        yaml_file,
                        resource_type,
                        param_spec,
                        all_resources=all_resources,
                    )  # found the correct spec, proceeding w/ test
                break

    for parameter in template_parameters:
        param = parameter.get("param")
        persistence = param_spec.get("persistent")

        if env_violation(yaml_file, param, spec.get("persistent")):
            human_text = "must" if persistence else "must not"
            human_text2 = "was not" if persistence else "was"

            invalid_parameters.append(
                "{} parameter {} {} be enumerated in an environment file, but "
                "parameter {} for {} {} found.".format(
                    resource_type, prop, human_text, param, yaml_file, human_text2
                )
            )

    assert not invalid_parameters, "\n".join(invalid_parameters)


def get_template_parameters(yaml_file, resource_type, spec, all_resources=False):
    parameters = []

    heat = Heat(yaml_file)
    if all_resources:
        resources = heat.resources
    else:
        resources = heat.get_resource_by_type(resource_type)

    for rid, resource_props in resources.items():
        for param in prop_iterator(resource_props, *spec.get("property")):
            if param and get_param(param) and param_helper(spec, get_param(param), rid):
                # this is first getting the param
                # then checking if its actually using get_param
                # then checking a custom helper function (mostly for internal vs external networks)
                parameters.append({"resource": rid, "param": get_param(param)})

    return parameters


def env_violation(yaml_file, parameter, persistent):
    # Returns True IF there's a violation, False if everything looks good.

    filepath, filename = os.path.split(yaml_file)
    environment_pair = get_environment_pair(yaml_file)
    if not environment_pair:  # this is a nested file perhaps?
        environment_pair = find_environment_file(
            yaml_file
        )  # we want to check parent env
        if not environment_pair:
            pytest.skip("unable to determine environment file for nested yaml file")

    env_yaml = environment_pair.get("eyml")
    parameters = env_yaml.get("parameters", {})
    in_env = False
    for param, value in parameters.items():
        if re.match(parameter, parameter):
            in_env = True
            break

    # confusing return. This function is looking for a violation.
    return not persistent == in_env


def param_helper(spec, param, rid):
    # helper function that has some predefined additional
    # checkers, mainly to figure out if internal/external network
    keeper = True
    for k, v in spec.get("kwargs").items():
        if k == "exclude_resource" and re.match(v, rid):
            keeper = False
            break
        elif k == "exclude_parameter" and re.match(v, param):
            keeper = False
            break

    return keeper


@validates("R-91125")
def test_nova_server_image_parameter_exists_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::Nova::Server", "image")


@validates("R-69431")
def test_nova_server_flavor_parameter_exists_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::Nova::Server", "flavor")


@categories("environment_file")
@validates("R-22838", "R-99812")
def test_nova_server_name_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "ALL", "name")


@categories("environment_file")
@validates("R-59568")
def test_nova_server_az_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::Nova::Server", "availability_zone")


@categories("environment_file")
@validates("R-20856")
def test_nova_server_vnf_id_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "vnf_id")


@categories("environment_file")
@validates("R-72871")
def test_nova_server_vf_module_id_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "vf_module_id")


@categories("environment_file")
@validates("R-37039")
def test_nova_server_vf_module_index_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "vf_module_index")


@categories("environment_file")
@validates("R-36542")
def test_nova_server_vnf_name_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "vnf_name")


@categories("environment_file")
@validates("R-80374")
def test_nova_server_vf_module_name_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "vf_module_name")


@categories("environment_file")
@validates("R-02691")
def test_nova_server_workload_context_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "workload_context")


@categories("environment_file")
@validates("R-13194")
def test_nova_server_environment_context_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", "environment_context")


@categories("environment_file")
@validates("R-29872")
def test_neutron_port_network_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::Neutron::Port", "network")


@categories("environment_file")
@validates("R-39841", "R-87123", "R-62590", "R-98905", "R-93030", "R-62590")
def test_neutron_port_external_fixedips_ipaddress_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(
        yaml_file,
        "OS::Neutron::Port",
        "fixed_ips",
        "ip_address",
        network_type="external",
    )


@validates("R-28795", "R-97201", "R-93496", "R-90206", "R-98569", "R-93496")
def test_neutron_port_internal_fixedips_ipaddress_parameter_exists_in_environment_file(
    yaml_file
):
    run_test_parameter(
        yaml_file,
        "OS::Neutron::Port",
        "fixed_ips",
        "ip_address",
        network_type="internal",
    )


@categories("environment_file")
@validates("R-83677", "R-80829", "R-69634", "R-22288")
def test_neutron_port_fixedips_subnet_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(
        yaml_file, "OS::Neutron::Port", "fixed_ips", "subnet", network_type="internal"
    )


@categories("environment_file")
@validates("R-83412", "R-83418")
def test_neutron_port_external_aap_ip_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_test_parameter(
        yaml_file,
        "OS::Neutron::Port",
        "allowed_address_pairs",
        "subnet",
        network_type="external",
    )


@categories("environment_file")
@validates("R-92193")
def test_network_fqdn_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "PLATFORM PROVIDED", r"^(.+?)_net_fqdn$")


@categories("environment_file")
@validates("R-76682")
def test_contrail_route_prefixes_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_test_parameter(
        yaml_file,
        "OS::ContrailV2::InterfaceRouteTable",
        "interface_route_table_routes",
        "interface_route_table_routes_route",
    )


@validates("R-50011")
def test_heat_rg_count_parameter_exists_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::Heat::ResourceGroup", "count")


@categories("environment_file")
@validates("R-100020", "R-100040", "R-100060", "R-100080", "R-100170")
def test_contrail_external_instance_ip_does_not_exist_in_environment_file(yaml_file):
    run_test_parameter(
        yaml_file,
        "OS::ContrailV2::InstanceIp",
        "instance_ip_address",
        network_type="external",
    )


@validates("R-100100", "R-100120", "R-100140", "R-100160", "R-100180")
def test_contrail_internal_instance_ip_does_exist_in_environment_file(yaml_file):
    run_test_parameter(
        yaml_file,
        "OS::ContrailV2::InstanceIp",
        "instance_ip_address",
        network_type="internal",
    )


@categories("environment_file")
@validates("R-100210", "R-100230", "R-100250", "R-100270")
def test_contrail_subnet_uuid_does_not_exist_in_environment_file(yaml_file):
    run_test_parameter(yaml_file, "OS::ContrailV2::InstanceIp", "subnet_uuid")


@categories("environment_file")
@validates("R-100320", "R-100340")
def test_contrail_vmi_aap_does_not_exist_in_environment_file(yaml_file):
    run_test_parameter(
        yaml_file,
        "OS::ContrailV2::VirtualMachineInterface",
        "virtual_machine_interface_allowed_address_pairs",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip_ip_prefix",
    )
