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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

"""heat parameters
"""
import pytest
from tests import cached_yaml as yaml
from tests.structures import Resource
from .helpers import validates

VERSION = "1.0.0"


def check_nested_parameter_doesnt_change(yaml_file):

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_parameters = []

    """
    checking if property: { get_param: parameter }, then property == parameter

    resource_id:
        type: nested.yaml
        properties:
            property: { get_param: parameter }

    resource_id:
        type: OS::Heat::ResourceGroup
        properties:
            resource_def:
                properties:
                    property: { get_param: parameter }
    """
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
            for k1, v1 in properties.items():
                if isinstance(v1, dict) and "get_param" in v1:
                    parameter = v1.get("get_param")
                    if isinstance(parameter, list):
                        parameter = parameter[0]

                    if k1 != parameter:
                        invalid_parameters.append(
                            {
                                "resource": r.resource_id,
                                "nested parameter": k1,
                                "parameter": parameter,
                                "file": yaml_file,
                            }
                        )

    assert (
        not invalid_parameters
    ), "Invalid parameter name change detected in nested template {}".format(
        invalid_parameters
    )


@validates("R-708564")
def test_parameter_name_doesnt_change_in_nested_template(yaml_file):
    check_nested_parameter_doesnt_change(yaml_file)
