# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2018 AT&T Intellectual Property. All rights reserved.
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
import os
import pytest

from .helpers import validates, get_environment_pair


def get_keys(template, key):
    """
    Gets the set of keys from an expected dict from the ``template`` mapped to
    the ``key``.  If the key is not found, or is not a dict, then an empty
    set is returned
    """
    value = template.get(key)
    if not value or not hasattr(value, "keys"):
        return set()
    else:
        return set(value.keys())


@pytest.mark.heat_only
@validates("R-01896", "R-26124")
def test_no_unused_parameters_between_env_and_templates(heat_template):
    """
    Check all defined parameters are used in the appropriate Heat template.
    """
    environment_pair = get_environment_pair(heat_template)
    if not environment_pair:
        pytest.skip("No heat/env pair could be identified")

    env_parameters = get_keys(environment_pair["eyml"], "parameters")
    template_parameters = get_keys(environment_pair["yyml"], "parameters")

    extra_in_template = template_parameters.difference(env_parameters)
    extra_in_env = env_parameters.difference(template_parameters)

    msg = (
        "Mismatched parameters detected for the template and environment pair "
        "({basename}). Ensure the parameters exist in both "
        "templates indented under their respective parameters sections. "
    )
    if extra_in_env:
        msg += (
            "The following parameters exist in the env file, but not the "
            "template: {extra_in_env}. "
        )
    if extra_in_template:
        msg += (
            "The following parameters exist in the template file, but not the "
            "environment file: {extra_in_template}"
        )

    assert not (extra_in_template or extra_in_env), msg.format(
        basename=os.path.split(environment_pair["name"])[-1],
        extra_in_env=", ".join(extra_in_env),
        extra_in_template=", ".join(extra_in_template),
    )
