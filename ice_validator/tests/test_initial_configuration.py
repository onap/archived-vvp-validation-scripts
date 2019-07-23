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
from os import path

import pytest
from yaml import YAMLError
from yaml.constructor import ConstructorError

from tests import cached_yaml as yaml
from tests.utils import yaml_custom_utils

from tests.helpers import validates, load_yaml
from tests.utils.nested_files import check_for_invalid_nesting
from tests.utils.nested_iterables import find_all_get_resource_in_yml
from tests.utils.nested_iterables import find_all_get_param_in_yml


@pytest.mark.base
@validates("R-95303")
def test_00_valid_yaml(filename):
    if path.splitext(filename)[-1].lower() not in (".yml", ".yaml", ".env"):
        pytest.skip("Not a YAML file")
    try:
        load_yaml(filename)
    except YAMLError as e:
        assert False, (
            "Invalid YAML detected: {} "
            "NOTE: Online YAML checkers such as yamllint.com "
            "can helpful in diagnosing errors in YAML"
        ).format(str(e).replace("\n", " "))


@pytest.mark.base
@validates("R-92635")
def test_02_no_duplicate_keys_in_file(yaml_file):
    """
    Checks that no duplicate keys exist in a given YAML file.
    """
    import yaml as normal_yaml  # we can't use the caching version in this test

    normal_yaml.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        yaml_custom_utils.raise_duplicates_keys,
    )

    try:
        with open(yaml_file) as fh:
            normal_yaml.safe_load(fh)
    except ConstructorError as e:
        pytest.fail("{} {}".format(e.problem, e.problem_mark))


@pytest.mark.base
@validates("R-92635")
def test_03_all_referenced_resources_exists(yaml_file):
    """
    Check that all resources referenced by get_resource
    actually exists in all yaml files
    """
    with open(yaml_file) as fh:
        yml = yaml.safe_load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the yaml file")

    resources = yml.get("resources")
    if resources:
        resource_ids = resources.keys()
        referenced_resource_ids = find_all_get_resource_in_yml(yml)

        missing_referenced_resources = set()
        for referenced_resource_id in referenced_resource_ids:
            if referenced_resource_id not in resource_ids:
                missing_referenced_resources.add(referenced_resource_id)

        assert not missing_referenced_resources, (
            "Unable to resolve get_resource for the following "
            "resource IDS: {}. Please ensure the resource ID is defined and "
            "nested under the resources section of the template".format(
                ", ".join(missing_referenced_resources)
            )
        )


@pytest.mark.base
@validates("R-92635")
def test_04_valid_nesting(yaml_file):
    """
    Check that the nesting is following the proper format and
    that all nested files exists and are parsable
    """
    invalid_nesting = []

    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    if "resources" in yml:
        try:
            invalid_nesting.extend(
                check_for_invalid_nesting(
                    yml["resources"], yaml_file, path.dirname(yaml_file)
                )
            )
        except Exception:
            invalid_nesting.append(yaml_file)

    assert not invalid_nesting, "invalid nested file detected in file {}\n\n".format(
        invalid_nesting
    )


@pytest.mark.base
@validates("R-92635")
def test_05_all_get_param_have_defined_parameter(yaml_file):
    """
    Check that all referenced parameters are actually defined
    as parameters
    """
    invalid_get_params = []
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    resource_params = find_all_get_param_in_yml(yml)

    parameters = set(yml.get("parameters", {}).keys())
    if not parameters:
        pytest.skip("no parameters detected")

    for rp in resource_params:
        if rp not in parameters:
            invalid_get_params.append(rp)

    assert (
        not invalid_get_params
    ), "get_param reference detected without corresponding parameter defined {}".format(
        invalid_get_params
    )


@validates("R-90152")
@pytest.mark.base
def test_06_heat_template_resource_section_has_resources(heat_template):

    found_resource = False

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    resources = yml.get("resources")
    if resources:
        for k1, v1 in yml["resources"].items():
            if not isinstance(v1, dict):
                continue

            found_resource = True
            break

    assert found_resource, "Heat templates must contain at least one resource"
