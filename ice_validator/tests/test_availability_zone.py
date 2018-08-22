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
"""test
"""

import re

import pytest
import yaml

from .helpers import validates

VERSION = "1.1.0"


@validates("R-98450")
def test_availability_zone_naming(heat_template):
    """
    Make sure all availability zones are properly formatted
    """

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_availability_zones = set()

    for v1 in yml["resources"].values():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if "type" not in v1:
            continue

        if v1["type"] == "OS::Nova::Server":
            for k2, v2 in v1["properties"].items():
                if k2 != "availability_zone":
                    continue
                if "str_replace" in v2:
                    continue
                if not re.match(r"availability_zone_\d+", v2["get_param"]):
                    invalid_availability_zones.add(v2["get_param"])

    assert not invalid_availability_zones, "invalid availability zones %s" % list(
        invalid_availability_zones
    )
