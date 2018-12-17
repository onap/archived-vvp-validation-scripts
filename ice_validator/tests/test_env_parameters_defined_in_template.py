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
import pytest

from .helpers import validates, get_environment_pair


@validates("R-599443")
def test_env_params_are_defined_in_template(heat_template):
    """Test that each paraemter defined in an environment file
    is also defined in the paired heat template"""

    bad = []
    template_pair = get_environment_pair(heat_template)

    if not template_pair:
        pytest.skip("No yaml/env pair could be determined")

    template = template_pair.get("yyml").get("parameters", {})
    environment = template_pair.get("eyml").get("parameters", {})

    if not isinstance(template, dict) or not isinstance(environment, dict):
        pytest.skip("No parameters defined in environment or template")

    template = template.keys()
    environment = environment.keys()

    for parameter in environment:
        if parameter not in template:
            bad.append(
                (
                    "{} is defined in the environment file but not in "
                    + "the template file "
                ).format(parameter)
            )
    msg = (
        "All parameters defined in an environment file must "
        + "be defined in the template file. "
        + ". ".join(bad)
    )

    assert not bad, msg
