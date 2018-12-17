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
import re

import pytest
from tests import cached_yaml as yaml

from .helpers import validates

VERSION = "1.0.0"

# pylint: disable=invalid-name


@validates("R-71699", "R-53952")
def test_no_http_resources(yaml_file):
    """Resources are prohibited from retrieving external
    yaml files"""
    is_url = re.compile(r"(?:http|https|file|ftp|ftps)://.+")

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_resources = []
    for rid, rprop in yml["resources"].items():
        rtype = rprop.get("type", "")
        if is_url.match(rtype):
            invalid_resources.append({"resource": rid, "url": rtype})
            continue

    assert not invalid_resources, "External resource types detected {}".format(
        invalid_resources
    )
