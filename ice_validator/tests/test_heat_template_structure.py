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


def test_heat_template_structure(yaml_file):
    '''
    Check that all heat templates only have the allowed sections
    '''
    key_values = ["heat_template_version", "description",
                  "parameter_groups", "parameters", "resources",
                  "outputs", "conditions"]

    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    assert any(map(lambda v: v in yml, key_values))


def test_heat_template_structure_contains_required_sections(yaml_file):
    '''
    Check that all heat templates have the required sections
    '''
    required_key_values = ["heat_template_version", "description",
                           "parameters", "resources"]

    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    assert any(map(lambda v: v in yml, required_key_values))


def test_heat_template_structure_sections_have_the_right_format(yaml_file):
    '''
    Check that all heat templates have sections of the right format.
    Do note that it only tests for dicts or not dicts currently.
    '''
    key_values = ["heat_template_version", "description",
                  "parameter_groups", "parameters", "resources",
                  "outputs", "conditions"]
    key_values_not_dicts = ["heat_template_version", "description"]

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

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
