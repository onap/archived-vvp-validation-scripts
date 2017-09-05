# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the “License”);
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
# under the Creative Commons License, Attribution 4.0 Intl. (the “License”);
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

import pytest
import yaml
import re


def test_nova_servers_correct_parameter_types(heat_template):
    '''
    Make sure all nova servers have properly assigned types for the parameters
    used for their name, image and flavor
    '''
    key_values = ["name", "flavor", "image"]
    key_value_formats = [
                        ["name", "string",
                            re.compile(r'(.+?)_name_\d+')],
                        ["name", "comma_delimited_list",
                            re.compile(r'(.+?)_names')],
                        ["flavor", "string",
                            re.compile(r'(.+?)_flavor_name')],
                        ["image", "string",
                            re.compile(r'(.+?)_image_name')],
                        ]

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    parameters = yml["parameters"]

    invalid_nova_servers = []

    for k1, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Nova::Server":
            continue

        valid_nova_server = True
        for k2, v2 in v1["properties"].items():
            if k2 not in key_values:
                continue
            formats = [v for v in key_value_formats if v[0] == k2]
            for v3 in formats:
                if "get_param" not in v2:
                    continue

                param = v2["get_param"]
                if isinstance(param, list):
                    param = param[0]

                m = v3[2].match(param)
                if m and m.group(1):
                    if parameters[param]:
                        param_spec = parameters[param]
                        if not param_spec["type"]:
                            valid_nova_server = False
                        elif param_spec["type"] != v3[1]:
                            valid_nova_server = False

        if not valid_nova_server:
            invalid_nova_servers.append(k1)

    assert not set(invalid_nova_servers)
