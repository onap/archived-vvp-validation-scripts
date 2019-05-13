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

"""heat parameters
"""
import pytest
from tests import cached_yaml as yaml
from tests.structures import Resource
from .helpers import validates, prop_iterator
import os

VERSION = "1.0.0"


def check_nested_parameter_doesnt_change(yaml_file, nresource_type, *nprops):
    """
    yaml_file: input heat template
    nresource_type: target resource type to look for in nested file
    nprops: list of props to dig through to get to parameter
    """
    base_dir, _ = os.path.split(yaml_file)
    invalid_parameters = []

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    for resource_id, resource in yml.get("resources", {}).items():
        resource_type = resource.get("type")
        if resource_type and (
            resource_type.endswith("yaml")
            or resource_type.endswith("yml")
            or resource_type == "OS::Heat::ResourceGroup"
        ):
            # workaround for subinterfaces
            metadata = resource.get("metadata")
            if metadata:
                subinterface_type = metadata.get("subinterface_type")
                if subinterface_type and subinterface_type == "network_collection":
                    continue

            r = Resource(resource_id=resource_id, resource=resource)
            properties = r.get_nested_properties()
            resources = r.get_nested_yaml(base_dir).get("resources", {})
            for nrid, nresource_dict in resources.items():  # iterate through nested file until found target r type

                if (
                    nresource_dict.get("type")
                    and nresource_dict.get("type") != nresource_type
                ):
                    continue

                for nparam in prop_iterator(nresource_dict, *nprops):  # get iterator of all target parameters
                    if nparam and "get_param" in nparam:  # iterator yields None if parameter isn't found
                        nparam = nparam.get("get_param")
                        for k1, v1 in properties.items():  # found nparam, now comparing to parent template
                            if isinstance(v1, dict) and "get_param" in v1:
                                parameter = v1.get("get_param")
                                # k1: nested resource parameter definition
                                # parameter: parent parameter name
                                # nparam: nested parameter name

                                # resolve list params like [param, { get_param: index }]
                                if isinstance(nparam, list):
                                    nparam = nparam[0]
                                if isinstance(parameter, list):
                                    parameter = parameter[0]

                                if k1 != nparam:  # we only care about the parameter we found in nested template
                                    continue

                                if k1 != parameter:
                                    msg = (
                                        "{} property {} cannot change when passed into "
                                        "a nested template. Nested parameter change detected in "
                                        "resource {}: parent parameter = {}, nested parameter = {}".format(
                                            nresource_type,
                                            nprops,
                                            resource_id,
                                            parameter,
                                            nparam,
                                        )
                                    )
                                    invalid_parameters.append(msg)

    assert not invalid_parameters, "\n".join(invalid_parameters)


# @validates("R-708564")
# def test_parameter_name_doesnt_change_in_nested_template(yaml_file):
#    check_nested_parameter_doesnt_change(yaml_file)

@validates("R-708564")
def test_server_name_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(heat_template, "OS::Nova::Server", "name")


@validates("R-708564")
def test_server_image_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(heat_template, "OS::Nova::Server", "image")


@validates("R-708564")
def test_server_flavor_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(heat_template, "OS::Nova::Server", "flavor")


@validates("R-708564")
def test_server_metadata_vnf_id_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vnf_id"
    )


@validates("R-708564")
def test_server_metadata_vf_module_id_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vf_module_id"
    )


@validates("R-708564")
def test_server_metadata_vnf_name_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vnf_name"
    )


@validates("R-708564")
def test_server_metadata_vf_module_name_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vf_module_name"
    )


@validates("R-708564")
def test_server_metadata_vm_role_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vm_role"
    )


@validates("R-708564")
def test_server_metadata_vf_module_index_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "vf_module_index"
    )


@validates("R-708564")
def test_server_metadata_workload_context_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "workload_context"
    )


@validates("R-708564")
def test_server_metadata_environment_context_parameter_name_doesnt_change_in_nested_template(
    heat_template
):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Nova::Server", "metadata", "environment_context"
    )


@validates("R-708564")
def test_port_network_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(heat_template, "OS::Neutron::Port", "network")


@validates("R-708564")
def test_port_fip_ip_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Neutron::Port", "fixed_ips", "ip_address"
    )


@validates("R-708564")
def test_port_fip_subnet_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Neutron::Port", "fixed_ips", "subnet"
    )


@validates("R-708564")
def test_port_aap_ip_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::Neutron::Port", "allowed_address_pairs", "ip_address"
    )


@validates("R-708564")
def test_vmi_net_ref_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::ContrailV2::VirtualMachineInterface", "virtual_network_refs"
    )


@validates("R-708564")
def test_vmi_aap_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template,
        "OS::ContrailV2::VirtualMachineInterface",
        "virtual_machine_interface_allowed_address_pairs",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip",
        "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip_ip_prefix"
    )


@validates("R-708564")
def test_iip_instance_ip_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::ContrailV2::InstanceIp", "instance_ip_address"
    )


@validates("R-708564")
def test_iip_subnet_uuid_parameter_name_doesnt_change_in_nested_template(heat_template):
    check_nested_parameter_doesnt_change(
        heat_template, "OS::ContrailV2::InstanceIp", "subnet_uuid"
    )
