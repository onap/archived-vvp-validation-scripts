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

from tests import cached_yaml as yaml
import pytest


def test_nova_servergroup_policies(yaml_file):
    """
    Check that nova servergroup resources using either anti-affinity or
    affinity rules in policies
    """
    req_rules = ["affinity", "anti-affinity"]

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_policies = []
    for r_id, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Nova::ServerGroup":
            continue
        if "policies" not in v1["properties"].keys():
            continue

        try:
            all_rules = v1["properties"]["policies"]
            detected_rules = set(all_rules) & set(req_rules)
            if len(detected_rules) == 0:
                invalid_policies.append(
                    "{} policies must include one of {}".format(
                        r_id, ", ".join(req_rules)
                    )
                )
            elif len(detected_rules) > 1:
                invalid_policies.append(
                    "{} policies must include only one of {}".format(
                        r_id, ", ".join(req_rules)
                    )
                )
        except ValueError:
            continue

    assert not invalid_policies, ". ".join(invalid_policies)
