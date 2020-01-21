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

"""Test heat template structure
"""
import pytest

from tests import cached_yaml as yaml
from .helpers import validates, is_base_module, load_yaml

VERSION = "1.2.0"

# pylint: disable=invalid-name


@validates("R-27078")
def test_heat_template_structure_contains_heat_template_version(yaml_file):
    """
    Check that all heat templates have the required sections
    """
    template = load_yaml(yaml_file)
    assert "heat_template_version" in template, "This template must contain a heat_template_version section"


@validates("R-39402")
def test_heat_template_structure_contains_description(yaml_file):
    """
    Check that all heat templates have the required sections
    """
    template = load_yaml(yaml_file)
    assert "description" in template, "This template must contain a description section"


@validates("R-35414")
def test_heat_template_structure_contains_parameters(heat_template):
    """
    Check that all heat templates have the required sections
    """
    if is_base_module(heat_template):
        pytest.skip("Not applicable to base modules")
    template = load_yaml(heat_template)
    assert "parameters" in template, "This template must contain a parameters section"


@validates("R-23664")
def test_heat_template_structure_contains_resources(heat_template):
    """
    Check that all heat templates have the required sections
    """
    if is_base_module(heat_template):
        pytest.skip("Not applicable to base modules")
    template = load_yaml(heat_template)
    assert "resources" in template, "This template must contain a resources section"


@validates("R-11441")
def test_parameter_type(yaml_file):
    """A VNF's Heat Orchestration Template's parameter type **MUST**
    be one of the following values:
    """
    types = ["string", "number", "json", "comma_delimited_list", "boolean"]
    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    for key, param in yml.get("parameters", {}).items():
        assert isinstance(param, dict), "%s parameter %s is not dict" % (yaml_file, key)
        if "type" not in param:
            continue
        typ = param["type"]
        assert typ in types, '%s parameter %s has invalid type "%s"' % (
            yaml_file,
            key,
            typ,
        )
