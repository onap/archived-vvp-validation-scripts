# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.network_roles import property_uses_get_resource


@validates("R-18008")
def test_neutron_port_network_param_is_string(yaml_file):
    """
    Make sure all network properties use the allowed naming
    conventions
    """
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    invalid_ports = []
    for k, v in yml["resources"].items():
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        if property_uses_get_resource(v, "network"):
            continue
        if v.get("type") != "OS::Neutron::Port":
            continue

        prop = v.get("properties", {}).get("network", {})
        network_param = prop.get("get_param", "") if isinstance(prop, dict) else ""
        if not network_param:
            continue

        param = yml.get("parameters").get(network_param)
        if not param:
            continue

        param_type = param.get("type")
        if not param_type:
            continue

        if param_type != "string":
            invalid_ports.append({"port": k, "param": network_param})

    assert not invalid_ports, "network parameter must be defined as string {} ".format(
        invalid_ports
    )
