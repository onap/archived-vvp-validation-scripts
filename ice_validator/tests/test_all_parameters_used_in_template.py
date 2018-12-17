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

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.nested_iterables import find_all_get_param_in_yml

VERSION = "1.0.0"

# pylint: disable=invalid-name


@validates("R-90279")
def test_all_parameters_used_in_template(yaml_file):

    invalid_params = []
    get_params = []
    skip_params = ["availability_zone"]

    with open(yaml_file, "r") as f:
        yml = yaml.load(f)

        template_parameters = yml.get("parameters")
        if not template_parameters:
            pytest.skip("no parameters found in template")

        get_params = find_all_get_param_in_yml(yml)
        if not get_params:
            pytest.skip("no get_params found in template")

    template_parameters = list(template_parameters.keys())
    for param in template_parameters:
        for sparam in skip_params:
            if param.find(sparam) != -1:
                template_parameters.remove(param)

    invalid_params = set(template_parameters) - set(get_params)

    assert not invalid_params, "Unused parameters detected in template {}".format(
        invalid_params
    )
