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

import re

import pytest
from tests import cached_yaml as yaml

from .helpers import validates


@validates("R-75141")
def test_alphanumeric_resource_ids_only(yaml_file):
    valid_format = re.compile(r"^[\w-]+$")

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_resource_ids = [
        k for k in yml["resources"].keys() if not valid_format.match(k)
    ]

    msg = "Invalid character(s) detected in the following resource IDs: " + ", ".join(
        invalid_resource_ids
    )
    assert not set(invalid_resource_ids), msg
