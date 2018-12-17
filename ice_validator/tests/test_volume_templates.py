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
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.nested_files import get_list_of_nested_files

import os
import pytest


@validates("R-270358")
def test_volume_templates_contains_cinder_or_resource_group(volume_template):
    """
    Check that all templates marked as volume templates are
    in fact volume templates
    """
    acceptable_resources = []

    with open(volume_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    dirname = os.path.dirname(volume_template)
    list_of_files = get_list_of_nested_files(yml, dirname)

    list_of_files.append(volume_template)

    for file in list_of_files:
        with open(file) as fh:
            yml = yaml.load(fh)

        for k, v in yml["resources"].items():
            if not isinstance(v, dict):
                continue
            if "type" not in v:
                continue
            if v["type"] in ["OS::Cinder::Volume", "OS::Heat::ResourceGroup"]:
                acceptable_resources.append(k)

    assert acceptable_resources, (
        "No OS::Cinder::Volume or OS::Heat::ResourceGroup resources "
        "found in volume module"
    )


@validates("R-55306")
def test_no_vf_module_index_in_cinder(volume_template):
    """
    vf_module_index is prohibited in volume templates
    """

    with open(volume_template) as fh:
        yml = yaml.load(fh)

    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")

    parameters = yml.get("parameters")
    if parameters and isinstance(parameters, dict):
        assert (
            "vf_module_index" not in parameters
        ), "{} must not use vf_module_index as a parameter".format(volume_template)
