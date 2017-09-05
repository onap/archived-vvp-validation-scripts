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


def test_parameter_valid_keys(yaml_file):
    '''
    Make sure each parameter is a dict and only contain
    valid keys
    '''
    key_values = ["type", "label", "description",
                  "hidden", "constraints", "immutable"]

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    invalid_params = []
    for v1 in yml["parameters"].values():
        if not isinstance(v1, dict):
            continue
        detected_keys = set(v1) & set(key_values)
        if set(v1) != set(detected_keys):
            invalid_params.append(v1)

    assert not set(invalid_params)


def test_default_values(yaml_file):
    '''
    Make sure no default values are set for any parameter.
    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    invalid_params = []
    for v1 in yml["parameters"].values():
        if not isinstance(v1, dict):
            continue
        if any(k == 'default' for k in v1):
            invalid_params.append(v1)

    assert not set(invalid_params)
