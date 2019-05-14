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

from tests.structures import Heat
from tests.utils import nested_dict
from .helpers import (
    validates,
    categories,
    get_environment_pair,
    find_environment_file,
    get_param,
)
import re
import pytest
from tests import cached_yaml as yaml

VERSION = "1.0.0"

# pylint: disable=invalid-name


def check_parameter_exists(pattern, parameters):
    if not parameters:
        return False

    for param in parameters:
        if pattern.search(param):
            return True

    return False


def check_param_in_env_file(environment_pair, param, DESIRED, exclude_parameter=None):

    # workaround for internal/external parameters
    if exclude_parameter and re.match(exclude_parameter, param):
        return False

    if not environment_pair:
        pytest.skip("No heat/env pair could be identified")

    env_file = environment_pair.get("eyml")

    pattern = re.compile(r"^{}$".format(param))

    if "parameters" not in env_file:
        pytest.skip("No parameters specified in the environment file")

    return (
        check_parameter_exists(pattern, env_file.get("parameters", {})) is not DESIRED
    )


"""
This function supports this structure, deviations
may or may not work without enhancement

resource_id:
    type: <resource_type>
    properties:
        prop0: { get_param: parameter_0 }
        prop1:  # this is a list of dicts
            - nested_prop_0: { get_param: parameter_1 }
            - nested_prop_1: { get_param: [parameter_2, {index}] }
        prop2:  # this is a dict of dicts
            nested_prop_0: { get_param: parameter_1 }
        prop3: { get_param: [parameter_3, 0]}
"""


def check_resource_parameter(
    environment_pair,
    prop,
    DESIRED,
    resource_type,
    resource_type_inverse=False,
    nested_prop="",
    exclude_resource="",
    exclude_parameter="",
):
    if not environment_pair:
        pytest.skip("No heat/env pair could be identified")

    env_file = environment_pair.get("eyml")
    template_file = environment_pair.get("yyml")

    if "parameters" not in env_file:
        pytest.skip("No parameters specified in the environment file")

    invalid_parameters = []
    if template_file:
        for resource, resource_prop in template_file.get("resources", {}).items():

            # workaround for subinterface resource groups
            if exclude_resource and re.match(exclude_resource, resource):
                continue

            if (
                resource_prop.get("type") == resource_type and not resource_type_inverse
            ) or (resource_prop.get("type") != resource_type and resource_type_inverse):

                pattern = False

                if not resource_prop.get("properties"):
                    continue

                resource_parameter = resource_prop.get("properties").get(prop)

                if not resource_parameter:
                    continue
                if isinstance(resource_parameter, list) and nested_prop:
                    for param in resource_parameter:
                        nested_param = param.get(nested_prop)
                        if not nested_param:
                            continue

                        if isinstance(nested_param, dict):
                            pattern = nested_param.get("get_param")
                        else:
                            pattern = ""

                        if not pattern:
                            continue

                        if isinstance(pattern, list):
                            pattern = pattern[0]

                        if check_param_in_env_file(
                            environment_pair,
                            pattern,
                            DESIRED,
                            exclude_parameter=exclude_parameter,
                        ):
                            invalid_parameters.append(pattern)

                elif isinstance(resource_parameter, dict):
                    if nested_prop and nested_prop in resource_parameter:
                        resource_parameter = resource_parameter.get(nested_prop)

                    pattern = resource_parameter.get("get_param")
                    if not pattern:
                        continue

                    if isinstance(pattern, list):
                        pattern = pattern[0]

                    if check_param_in_env_file(
                        environment_pair,
                        pattern,
                        DESIRED,
                        exclude_parameter=exclude_parameter,
                    ):
                        invalid_parameters.append(pattern)
                else:
                    continue

    return set(invalid_parameters)


def run_check_resource_parameter(
    yaml_file, prop, DESIRED, resource_type, check_resource=True, **kwargs
):
    filepath, filename = os.path.split(yaml_file)
    environment_pair = get_environment_pair(yaml_file)

    if not environment_pair:
        # this is a nested file

        if not check_resource:
            # dont check env for nested files
            # This will be tested separately for parent template
            pytest.skip("This test doesn't apply to nested files")

        environment_pair = find_environment_file(yaml_file)
        if environment_pair:
            with open(yaml_file, "r") as f:
                yml = yaml.load(f)
            environment_pair["yyml"] = yml
        else:
            pytest.skip("unable to determine environment file for nested yaml file")

    if check_resource:
        invalid_parameters = check_resource_parameter(
            environment_pair, prop, DESIRED, resource_type, **kwargs
        )
    else:
        invalid_parameters = check_param_in_env_file(environment_pair, prop, DESIRED)

    if kwargs.get("resource_type_inverse"):
        resource_type = "non-{}".format(resource_type)

    assert not invalid_parameters, (
        "{} {} parameters in template {}{}"
        " found in {} environment file: {}".format(
            resource_type,
            prop,
            filename,
            " not" if DESIRED else "",
            environment_pair.get("name"),
            ", ".join(invalid_parameters),
        )
    )


@validates("R-91125")
def test_nova_server_image_parameter_exists_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "image", True, "OS::Nova::Server")


@validates("R-69431")
def test_nova_server_flavor_parameter_exists_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "flavor", True, "OS::Nova::Server")


@categories("environment_file")
@validates("R-22838")
def test_nova_server_name_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "name", False, "OS::Nova::Server")


@categories("environment_file")
@validates("R-59568")
def test_nova_server_az_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file, "availability_zone", False, "OS::Nova::Server"
    )


@categories("environment_file")
@validates("R-20856")
def test_nova_server_vnf_id_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "vnf_id", False, "", check_resource=False)


@categories("environment_file")
@validates("R-72871")
def test_nova_server_vf_module_id_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file, "vf_module_id", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-37039")
def test_nova_server_vf_module_index_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file, "vf_module_index", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-36542")
def test_nova_server_vnf_name_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "vnf_name", False, "", check_resource=False)


@categories("environment_file")
@validates("R-80374")
def test_nova_server_vf_module_name_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file, "vf_module_name", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-02691")
def test_nova_server_workload_context_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file, "workload_context", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-13194")
def test_nova_server_environment_context_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file, "environment_context", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-29872")
def test_neutron_port_network_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(yaml_file, "network", False, "OS::Neutron::Port")


@categories("environment_file")
@validates("R-39841", "R-87123", "R-62590", "R-98905", "R-93030", "R-62590")
def test_neutron_port_external_fixedips_ipaddress_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file,
        "fixed_ips",
        False,
        "OS::Neutron::Port",
        nested_prop="ip_address",
        exclude_parameter=re.compile(r"^(.+?)_int_(.+?)$"),
    )


@validates("R-28795", "R-97201", "R-93496", "R-90206", "R-98569", "R-93496")
def test_neutron_port_internal_fixedips_ipaddress_parameter_exists_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file,
        "fixed_ips",
        True,
        "OS::Neutron::Port",
        nested_prop="ip_address",
        exclude_parameter=re.compile(r"^((?!_int_).)*$"),
    )


@categories("environment_file")
@validates("R-83677", "R-80829", "R-69634", "R-22288")
def test_neutron_port_fixedips_subnet_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file, "fixed_ips", False, "OS::Neutron::Port", nested_prop="subnet"
    )


@categories("environment_file")
@validates("R-83412", "R-83418")
def test_neutron_port_external_aap_ip_parameter_doesnt_exist_in_environment_file(
    yaml_file
):
    run_check_resource_parameter(
        yaml_file,
        "allowed_address_pairs",
        False,
        "OS::Neutron::Port",
        nested_prop="ip_address",
        exclude_parameter=re.compile(r"^(.+?)_int_(.+?)$"),
    )


@categories("environment_file")
@validates("R-99812")
def test_non_nova_server_name_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file, "name", False, "OS::Nova::Server", resource_type_inverse=True
    )


@categories("environment_file")
@validates("R-92193")
def test_network_fqdn_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file, r"^(.+?)_net_fqdn$", False, "", check_resource=False
    )


@categories("environment_file")
@validates("R-76682")
def test_contrail_route_prefixes_parameter_doesnt_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file,
        "interface_route_table_routes",
        False,
        "OS::ContrailV2::InterfaceRouteTable",
        nested_prop="interface_route_table_routes_route",
    )


@validates("R-50011")
def test_heat_rg_count_parameter_exists_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file,
        "count",
        True,
        "OS::Heat::ResourceGroup",
        exclude_resource=re.compile(r"^(.+?)_subint_(.+?)_port_(.+?)_subinterfaces$"),
    )


@categories("environment_file")
@validates("R-100020", "R-100040", "R-100060", "R-100080", "R-100170")
def test_contrail_external_instance_ip_does_not_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file,
        "instance_ip_address",
        False,
        "OS::ContrailV2::InstanceIp",
        exclude_resource=re.compile(r"^.*_int_.*$"),  # exclude internal IPs
    )


@validates("R-100100", "R-100120", "R-100140", "R-100160", "R-100180")
def test_contrail_internal_instance_ip_does_not_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file,
        "instance_ip_address",
        True,
        "OS::ContrailV2::InstanceIp",
        exclude_resource=re.compile(r"(?!.*_int_.*)"),  # exclude external IPs
    )


@categories("environment_file")
@validates("R-100210", "R-100230", "R-100250", "R-100270")
def test_contrail_subnet_uuid_does_not_exist_in_environment_file(yaml_file):
    run_check_resource_parameter(
        yaml_file, "subnet_uuid", False, "OS::ContrailV2::InstanceIp"
    )


@categories("environment_file")
@validates("R-100320", "R-100340")
def test_contrail_vmi_aap_does_not_exist_in_environment_file(yaml_file):
    # This test needs to check a more complex structure.  Rather than try to force
    # that into the existing run_check_resource_parameter logic we'll just check it
    # directly
    pairs = get_environment_pair(yaml_file)
    if not pairs:
        pytest.skip("No matching env file found")
    heat = Heat(filepath=yaml_file)
    env_parameters = pairs["eyml"].get("parameters") or {}
    vmis = heat.get_resource_by_type("OS::ContrailV2::VirtualMachineInterface")
    external_vmis = {rid: data for rid, data in vmis.items() if "_int_" not in rid}
    invalid_params = []
    for r_id, vmi in external_vmis.items():
        aap_value = nested_dict.get(
            vmi,
            "properties",
            "virtual_machine_interface_allowed_address_pairs",
            "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
        )
        if not aap_value or not isinstance(aap_value, list):
            # Skip if aap not used or is not a list.
            continue
        for pair_ip in aap_value:
            if not isinstance(pair_ip, dict):
                continue  # Invalid Heat will be detected by another test
            settings = (
                pair_ip.get(
                    "virtual_machine_interface_allowed_address"
                    "_pairs_allowed_address_pair_ip"
                )
                or {}
            )
            if isinstance(settings, dict):
                ip_prefix = (
                    settings.get(
                        "virtual_machine_interface_allowed_address"
                        "_pairs_allowed_address_pair_ip_ip_prefix"
                    )
                    or {}
                )
                ip_prefix_param = get_param(ip_prefix)
                if ip_prefix_param and ip_prefix_param in env_parameters:
                    invalid_params.append(ip_prefix_param)

    msg = (
        "OS::ContrailV2::VirtualMachineInterface "
        "virtual_machine_interface_allowed_address_pairs"
        "_allowed_address_pair_ip_ip_prefix "
        "parameters found in environment file {}: {}"
    ).format(pairs.get("name"), ", ".join(invalid_params))
    assert not invalid_params, msg
