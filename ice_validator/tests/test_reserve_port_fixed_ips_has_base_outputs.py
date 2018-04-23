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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

import pytest
from os import path, sep
import yaml
from .utils.ports import is_reserved_port


def test_reserve_port_fixed_ips_has_base_outputs(heat_template):
    '''
    Make sure all fixed ips specified in reserved ports are
    also exported as outputs in the same base template
    '''
    basename = path.splitext(heat_template)[0].rsplit(sep, 1)[1]
    if not (basename.endswith("_base") or
            basename.startswith("base_") or
            basename.find("_base_") > 0):
            pytest.skip("Skipping as it is not a base template")

    # parse the yml
    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # get the outputs
    try:
        outputs = yml["outputs"]
    except (TypeError, KeyError):
        outputs = {}

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_fixed_ips = []
    for k1, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Neutron::Port":
            continue
        if not is_reserved_port(k1):
            continue

        for k2, v2 in v1["properties"].items():
            if k2 != "fixed_ips":
                continue
            for v3 in v2:
                if "ip_address" not in v3:
                    continue
                if "get_param" not in v3["ip_address"]:
                    continue

                param = v3["ip_address"]["get_param"]

                # construct the expected output param
                if 'v6' in param:
                    output_param = param.replace('floating_v6_ip', 'v6_vip')
                else:
                    output_param = param.replace('floating_ip', 'vip')

                # check the output is constructed correctly
                try:
                    output_vip = outputs[output_param]
                    if not output_vip:
                        invalid_fixed_ips.append(param)
                    else:
                        # make sure the value is set properly using the
                        # original param value
                        output_value_param = output_vip["value"]["get_param"]
                        if output_value_param != param:
                            invalid_fixed_ips.append(param)
                except (TypeError, KeyError):
                    invalid_fixed_ips.append(param)

    assert not set(invalid_fixed_ips)
