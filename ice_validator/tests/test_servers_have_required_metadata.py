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


def test_servers_have_required_metadata(yaml_file):
    '''
    Check all defined nova server instances have the required metadata:
    vnf_id and vf_module_id
    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # Check if the param vm_role is defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    required_metadata = ["vnf_id", "vf_module_id", "vnf_name"]

    invalid_nova_servers = []
    for k, v in yml["resources"].items():
        if v.get("type") != "OS::Nova::Server":
            continue
        if 'properties' not in v:
            continue
        if 'metadata' not in v['properties']:
            continue

        # do not add the server if it has the required metadata
        if set(required_metadata) <= set(v["properties"]["metadata"].keys()):
            continue
        invalid_nova_servers.append(k)

    assert not set(invalid_nova_servers)
