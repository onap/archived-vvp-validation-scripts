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
#
"""test
"""

import re

import pytest
from tests import cached_yaml as yaml
from tests.utils import nested_files

from .helpers import validates, is_nova_server

VERSION = "1.1.0"


@validates("R-98450")
def test_availability_zone_naming(yaml_file):
    """
    Make sure all availability zones are properly formatted
    """

    if nested_files.file_is_a_nested_template(yaml_file):
        pytest.skip("test does not apply to nested files")

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_availability_zones = set()

    for k1, v1 in yml["resources"].items():
        if not is_nova_server(v1):
            continue

        for k2, v2 in v1["properties"].items():
            if k2 != "availability_zone" or "str_replace" in v2:
                continue
            if "get_param" not in v2:
                invalid_availability_zones.add(k1)
                continue
            if not isinstance(v2["get_param"], str):
                continue
            if not re.match(r"availability_zone_\d+", v2["get_param"]):
                invalid_availability_zones.add(v2["get_param"])

    assert not invalid_availability_zones, "invalid availability zones %s" % list(
        invalid_availability_zones
    )
