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


def test_subnet_format_use_get_param_or_get_resource(heat_template):
    '''
    Make sure all subnet properties only use get_parm
    or get_resource of an internal network
    '''

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_subnets = []
    for v1 in yml["resources"].values():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Neutron::Port":
            continue

        # get the network param to define the network_type
        try:
            network_param = v1["properties"]["network"]["get_param"]
        except KeyError:
            continue

        # define the network_type
        network_type = 'external'
        if network_param.startswith('int_'):
            network_type = 'internal'

        for k2, v2 in v1["properties"].items():
            if k2 != "fixed_ips":
                continue

            for v3 in v2:
                if "subnet_id" not in v3:
                    continue

                subnet_id = v3["subnet_id"]

                # get the param or resource
                if network_type == "external" and\
                   subnet_id.get("get_param"):
                    continue
                elif network_type == "internal" and\
                    (subnet_id.get("get_param") or
                     subnet_id.get("get_resource")):
                    continue
                else:
                    invalid_subnets.append(subnet_id)

    assert not set(invalid_subnets)
