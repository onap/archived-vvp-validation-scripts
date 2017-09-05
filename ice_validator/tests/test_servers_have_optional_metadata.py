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


def test_servers_have_optional_metadata(yaml_file):
    '''
    Check that if optional metadata is included in the metadata
    for nova servers, they are specified in parameters
    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    # Check if the param vm_role is defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    optional_metadata = ["vf_module_name", "vf_module_index"]
    specified_optional_metadata = [k
                                   for k in yml["parameters"].keys()
                                   if k in optional_metadata]

    need_optional_metadata = []
    for v in yml["resources"].values():
        keys = []
        if v.get("type") == "OS::Nova::Server":
            if 'properties' not in v:
                continue
            if 'metadata' not in v['properties']:
                continue

            keys = v["properties"]["metadata"].keys()
        elif v.get("type") == "OS::Heat::ResourceGroup":
            if 'resource_def' not in v:
                continue
            if 'properties' not in v['resource_def']:
                continue

            keys = v["resource_def"]["properties"].keys()

        for key in keys:
            if key in optional_metadata:
                need_optional_metadata.append(key)

    if not need_optional_metadata:
        pytest.skip("No optional metadata is specified in the heat template")

    # Check that if optional metadata is included in the metadata
    # for nova servers, they are specified in parameters
    assert set(specified_optional_metadata) == set(need_optional_metadata)
