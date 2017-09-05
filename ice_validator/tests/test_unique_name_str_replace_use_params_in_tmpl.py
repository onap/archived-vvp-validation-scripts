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

import yaml
import pytest


def test_unique_name_str_replace_use_req_params_in_tmpl(yaml_file):
    '''
    Check that all occurences of str_replace uses either vnf_name or
    vnf_module_id to construct the name
    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    in_template = []
    for v1 in yml["resources"].values():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1["type"] in ["OS::Nova::Server", "OS::Neutron::Port",
                          "OS::Heat::ResourceGroup"]:
            continue

        try:
            v2 = v1["properties"]["name"]
            str_replace = v2["str_replace"]
            params = str_replace["params"]
            template = str_replace["template"]
            in_template.append(all(k3 in template for k3 in params))
        except (TypeError, KeyError):
            continue

    if not in_template:
        pytest.skip("No str_replace instances were detected")

    assert all(c for c in in_template)
