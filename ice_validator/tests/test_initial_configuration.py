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

from os import path

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from yamllint.config import YamlLintConfig
from yamllint import linter
from .utils.nested_files import check_for_invalid_nesting
from .utils.nested_iterables import find_all_get_resource_in_yml
from .utils.nested_iterables import find_all_get_param_in_yml

"""
Order tests by number so they execute in order for base tests
"""


@pytest.mark.base
@validates('R-95303')
def test_00_valid_yaml(filename):
    '''
    Read in each .yaml or .env file. If it is successfully parsed as yaml, save
    contents, else add filename to list of bad yaml files. Log the result of
    parse attempt.
    '''
    conf = YamlLintConfig('rules: {}')

    if path.splitext(filename)[-1] in [".yml", ".yaml", ".env"]:
        gen = linter.run(open(filename), conf)
        errors = list(gen)

        assert not errors, "Error parsing file {} with error {}".format(filename, errors)
    else:
        pytest.skip("The file does not have any of the extensions .yml,\
            .yaml, or .env")


@pytest.mark.base
def test_02_all_referenced_resources_exists(yaml_file):
    '''
    Check that all resources referenced by get_resource
    actually exists in all yaml files
    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the yaml file")

    resource_ids = yml['resources'].keys()
    referenced_resource_ids = find_all_get_resource_in_yml(yml)

    missing_referenced_resources = set()
    for referenced_resource_id in referenced_resource_ids:
        if referenced_resource_id not in resource_ids:
            missing_referenced_resources.add(referenced_resource_id)

    assert not missing_referenced_resources, (
        'missing referenced resources %s' % list(
            missing_referenced_resources))


@pytest.mark.base
def test_01_valid_nesting(yaml_file):
    '''
    Check that the nesting is following the proper format and
    that all nested files exists and are parsable
    '''
    invalid_nesting = []

    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    if "resources" in yml:
        try:
            invalid_nesting.extend(check_for_invalid_nesting(
                yml["resources"],
                yaml_file,
                path.dirname(yaml_file)))
        except Exception:
            invalid_nesting.append(yaml_file)

    assert not invalid_nesting, \
        "invalid nested file detected in file {}\n\n".format(invalid_nesting)


@pytest.mark.base
def test_03_all_get_param_have_defined_parameter(yaml_file):
    '''
    Check that all referenced parameters are actually defined
    as parameters
    '''
    invalid_get_params = []
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    resource_params = find_all_get_param_in_yml(yml)

    parameters = set(yml.get('parameters', {}).keys())
    if not parameters:
        pytest.skip("no parameters detected")

    for rp in resource_params:
        if rp not in parameters:
            invalid_get_params.append(rp)

    assert not invalid_get_params, (
        "get_param reference detected without corresponding parameter defined {}"
        .format(invalid_get_params))
