# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
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
"""test
"""
import pytest
from tests import cached_yaml as yaml

from .helpers import validates

VERSION = "1.1.0"


def check_parameter_type(heat_template, parameter, parameter_type):
    """
    Make sure these OS::Nova::Server parameters are defined w/
    the correct type
    """

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    invalid_parameters = []

    for k1, v1 in yml["parameters"].items():
        if not isinstance(v1, dict):
            continue
        if "type" not in v1:
            continue

        if k1.find(parameter) == -1:
            continue

        param_type = v1.get("type")

        if not param_type:
            continue

        if param_type != parameter_type:
            invalid_parameters.append(k1)

    assert (
        not invalid_parameters
    ), "{} parameters must be defined as type {}: {}".format(
        parameter, parameter_type, invalid_parameters
    )


def check_server_parameter_name(heat_template, parameter, parameter_name):
    """
    Check each OS::Nova::Server metadata property
    uses the same parameter name w/ get_param
    """

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_parameters = []

    for k1, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "type" not in v1:
            continue

        if v1["type"] != "OS::Nova::Server":
            continue

        metadata = v1.get("properties", {}).get("metadata", {}).get(parameter)

        if not metadata or not isinstance(metadata, dict):
            continue

        get_param = metadata.get("get_param")

        if not get_param:
            continue

        if get_param != parameter_name:
            invalid_parameters.append(
                {
                    "resource": k1,
                    "metadata property": parameter_name,
                    "get_param": get_param,
                }
            )

    assert not invalid_parameters, (
        "metadata property {} must use get_param and "
        "the parameter name must be {}: {}".format(
            parameter, parameter_name, invalid_parameters
        )
    )


@validates("R-23311")
def test_availability_zone_parameter_type(heat_template):
    check_parameter_type(heat_template, "availability_zone_", "string")


@validates("R-07507")
def test_vnf_id_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vnf_id", "string")
    check_server_parameter_name(heat_template, "vnf_id", "vnf_id")


@validates("R-82134")
def test_vf_module_id_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vf_module_id", "string")
    check_server_parameter_name(heat_template, "vf_module_id", "vf_module_id")


@validates("R-62428")
def test_vnf_name_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vnf_name", "string")
    check_server_parameter_name(heat_template, "vnf_name", "vnf_name")


@validates("R-39067")
def test_vf_module_name_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vf_module_name", "string")
    check_server_parameter_name(heat_template, "vf_module_name", "vf_module_name")


@validates("R-95430")
def test_vm_role_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vm_role", "string")
    check_server_parameter_name(heat_template, "vm_role", "vm_role")


@validates("R-54340")
def test_vf_module_index_parameter_type_and_parameter_name(heat_template):
    check_parameter_type(heat_template, "vf_module_index", "number")
    check_server_parameter_name(heat_template, "vf_module_index", "vf_module_index")
