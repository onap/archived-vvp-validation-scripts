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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

"""heat parameters
"""

import pytest
from tests import cached_yaml as yaml
from tests.structures import Resource

from .helpers import validates

VERSION = "1.0.0"


def check_nested_parameter_doesnt_change(yaml_file, parameter):

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_parameters = []

    """
    checking if property: { get_param: <parameter> }, then property == <parameter>

    resource_id:
        type: nested.yaml
        properties:
            property: { get_param: <parameter> }

    resource_id:
        type: OS::Heat::ResourceGroup
        properties:
            resource_def:
                properties:
                    property: { get_param: <parameter> }
    """
    for resource_id, resource in yml.get("resources", {}).items():
        r = Resource(resource_id=resource_id, resource=resource)
        properties = r.get_nested_properties()
        for k1, v1 in properties.items():
            if (
                isinstance(v1, dict)
                and "get_param" in v1
                and parameter == v1.get("get_param")
            ):
                if k1 != parameter:
                    invalid_parameters.append(
                        {
                            "resource": r.resource_id,
                            "nested parameter": k1,
                            "parameter": parameter,
                        }
                    )

    assert (
        not invalid_parameters
    ), "Invalid parameter name change detected in nested template {}".format(
        invalid_parameters
    )


@validates("R-70757")
def test_vm_role_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vm_role")


@validates("R-44491")
def test_vnf_id_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vnf_id")


@validates("R-86237")
def test_vf_module_id_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vf_module_id")


@validates("R-16576")
def test_vnf_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vnf_name")


@validates("R-49177")
def test_vf_module_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vf_module_name")


@validates("R-22441")
def test_vf_module_index_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "vf_module_index")


@validates("R-62954")
def test_environment_context_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "environment_context")


@validates("R-75202")
def test_workload_context_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file, "workload_context")
