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


def test_fixed_ips_format_use_get_parm(heat_template):
    '''
    Make sure all fixed_ips properties only use get_param
    '''
    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_fixed_ips = []
    for k, v in yml["resources"].items():
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        if v.get("type") != "OS::Neutron::Port":
            continue

        valid_fixed_ip = True
        for k2, v2 in v["properties"].items():
            if k2 != "fixed_ips":
                continue
            for v3 in v2:
                if "ip_address" not in v3:
                    continue
                if "get_param" not in v3["ip_address"]:
                    valid_fixed_ip = False

        if not valid_fixed_ip:
            invalid_fixed_ips.append(k)

    assert not set(invalid_fixed_ips)
