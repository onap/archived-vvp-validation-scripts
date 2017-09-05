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

import yaml
import pytest


def test_environment_structure(env_file):
    '''
    Check that all environments files only have the allowed sections
    '''
    key_values = ["parameters", "event_sinks", "encrypted_parameters",
                  "parameter_merge_strategies"]

    with open(env_file) as fh:
        yml = yaml.load(fh)
    assert any(map(lambda v: v in yml, key_values))


def test_environment_file_contains_required_sections(env_file):
    '''
    Check that all environments files only have the allowed sections
    '''
    required_key_values = ["parameters"]

    with open(env_file) as fh:
        yml = yaml.load(fh)
    assert any(map(lambda v: v in yml, required_key_values))


def test_environment_file_sections_have_the_right_format(env_file):
    '''
    Check that all environment files have sections of the right format.
    Do note that it only tests for dicts or not dicts currently.
    '''
    key_values = ["parameters", "event_sinks", "encrypted_parameters",
                  "parameter_merge_strategies"]
    key_values_not_dicts = ["event_sinks"]

    with open(env_file) as fh:
        yml = yaml.load(fh)

    if not any(map(lambda v: v in yml, key_values)):
        pytest.skip('The fixture is not applicable for this test')

    is_dict = 0
    should_be_dict = 0
    is_not_dict = 0
    should_not_be_dict = 0
    for key_value in key_values:
        if key_value in yml:
            if isinstance(yml[key_value], dict):
                is_dict += 1
                if key_value not in key_values_not_dicts:
                    should_be_dict += 1
            elif not isinstance(yml[key_value], list):
                is_not_dict += 1
                if key_value in key_values_not_dicts:
                    should_not_be_dict += 1
    assert (is_dict == should_be_dict and
            is_not_dict == should_not_be_dict)
