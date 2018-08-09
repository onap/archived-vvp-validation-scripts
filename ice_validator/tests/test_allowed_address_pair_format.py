# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
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

'''
test_allowed_address_pairs_format
'''

import re

import pytest
import yaml

from .utils.network_roles import get_network_role_from_port, \
    property_uses_get_resource

VERSION = '1.0.0'

# pylint: disable=invalid-name


def test_allowed_address_pairs_format(heat_template):
    '''
    Make sure all allowed_address_pairs properties follow the allowed
    naming conventions
    '''
    allowed_formats = [
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_floating_v6_ip')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_floating_ip')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_floating_v6_ip')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_floating_ip')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_v6_ip_\d+')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_ip_\d+')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_v6_ip_\d+')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_ip_\d+')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "internal", re.compile(r'(.+?)_int_(.+?)_v6_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "internal", re.compile(r'(.+?)_int_(.+?)_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "external", re.compile(r'(.+?)_v6_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "external", re.compile(r'(.+?)_ips')],
                      ]

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    # check both valid and invalid patterns to catch edge cases
    invalid_allowed_address_pairs = []

    for v1 in yml["resources"].values():
        if (not isinstance(v1, dict)
                or "properties" not in v1
                or v1.get("type") != "OS::Neutron::Port"
                or property_uses_get_resource(v1, "network")):
            continue
        network_role = get_network_role_from_port(v1)

        v2 = v1["properties"].get("allowed_address_pairs", {})
        for v3 in v2:
            if ("ip_address" not in v3
                    or "get_param" not in v3["ip_address"]):
                continue

            param = v3["ip_address"]["get_param"]
            if isinstance(param, list):
                param = param[0]

            for v4 in allowed_formats:
                # check if pattern matches
                m = v4[3].match(param)
                if m:
                    if (v4[2] == "internal"
                            and len(m.groups()) > 1
                            and m.group(2) == network_role):
                        break
                    elif (v4[2] == "external"
                            and len(m.groups()) > 0
                            and m.group(1).endswith("_" + network_role)):
                        break
            else:
                invalid_allowed_address_pairs.append(param)

    assert not set(invalid_allowed_address_pairs), (
            'invalid_allowed_address_pairs %s' % list(
                    set(invalid_allowed_address_pairs)))
