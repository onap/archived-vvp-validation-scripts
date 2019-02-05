# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2019 AT&T Intellectual Property. All rights reserved.
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
import re

import pytest
from six import string_types

from tests.helpers import validates, get_environment_pair
from tests.structures import Heat


@validates("R-86476")
def test_vm_role_hardcoded(yaml_file):
    """
    Validate vm_role value when hardcoded in the template
    """
    heat = Heat(filepath=yaml_file)
    servers = heat.get_resource_by_type("OS::Nova::Server")
    errors = []
    for r_id, server in servers.items():
        props = server.get("properties") or {}
        metadata = props.get("metadata") or {}
        if "vm_role" not in metadata:
            continue
        vm_role_value = metadata["vm_role"]
        if isinstance(vm_role_value, dict):
            continue  # Likely using get_param - validate separately
        if not re.match(r"^\w+$", vm_role_value):
            errors.append(
                "OS::Nova::Server {} vm_role = {}".format(r_id, vm_role_value)
            )

    msg = (
        "vm_role's value must only contain alphanumerics and underscores. "
        + "Invalid vm_role's detected: "
        + ". ".join(errors)
    )
    assert not errors, msg


@validates("R-86476")
def test_vm_role_from_env_file(yaml_file):
    """
    Validate vm_role when using parameters and env file
    """
    pair = get_environment_pair(yaml_file)
    if not pair:
        pytest.skip("Unable to resolve environment pair")
    template_params = pair["yyml"].get("parameters") or {}
    env_params = pair["eyml"].get("parameters") or {}

    if "vm_role" not in template_params:
        pytest.skip("vm_role not in parameters")

    if "vm_role" not in env_params:
        pytest.skip("vm_role not in environment file.  Error checked elsewhere")

    vm_role = env_params.get("vm_role", "")
    if not isinstance(vm_role, string_types):
        vm_role = str(vm_role)
    msg = "vm_role {} contains non-alphanumeric or non-underscore characters".format(
        vm_role
    )
    assert re.match(r"^\w+$", vm_role), msg
