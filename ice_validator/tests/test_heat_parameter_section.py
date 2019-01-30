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

"""parameters
"""

import re

import pytest
from tests import cached_yaml as yaml

from .helpers import validates

VERSION = "1.0.0"

# one or more (alphanumeric or underscore)
RE_VALID_PARAMETER_NAME = re.compile(r"[\w_]+$")


@validates("R-90526")
def test_default_values(yaml_file):
    """
    Make sure no default values are set for any parameter.
    """
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    invalid_params = set()
    for param, v1 in yml["parameters"].items():
        if not isinstance(v1, dict):
            continue
        if any(k == "default" for k in v1):
            invalid_params.add(param)

    msg = "The following parameters specify a default: {}".format(
        ", ".join(invalid_params)
    )
    assert not invalid_params, msg


@validates("R-25877")
def test_parameter_names(yaml_file):
    """
    A VNF's Heat Orchestration Template's parameter name
    (i.e., <param name>) **MUST** contain only alphanumeric
    characters and underscores ('_').
    """
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    for key in yml["parameters"]:
        assert RE_VALID_PARAMETER_NAME.match(
            key
        ), '%s parameter "%s" not alphanumeric or underscore' % (yaml_file, key)
