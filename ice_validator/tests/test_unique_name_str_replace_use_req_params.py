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

from tests import cached_yaml as yaml
import pytest

from tests.helpers import validates


@validates("R-85734")
def test_unique_name_str_replace_use_req_params(yaml_file):
    """
    Check that all occurences of str_replace uses either vnf_name or
    vf_module_id to construct the name
    """
    req_params = {"vnf_name"}

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    missing_req_params = []
    for r_id, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1["type"] in ["OS::Nova::Server"]:
            continue

        try:
            v2 = v1["properties"]["name"]
            str_replace = v2["str_replace"]

            all_params = set()
            for v3 in str_replace["params"].values():
                all_params.add(v3["get_param"])
            if req_params.difference(all_params):
                msg = (
                    "Resource({}) does not use str_replace "
                    "and the vnf_name parameter to set "
                    "the name property"
                ).format(r_id)
                missing_req_params.append(msg)
        except (TypeError, KeyError):
            continue

    assert not missing_req_params, ", ".join(missing_req_params)
