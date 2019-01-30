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
#

import pytest
from tests import cached_yaml as yaml

from .helpers import validates


@validates("R-93177")
def test_network_format_use_get_param_or_get_resource(heat_template):
    """
    Make sure all network properties only use get_param
    or get_resource of an internal network
    """

    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_get_resource = []
    invalid_get_param = []
    for k1, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Neutron::Port":
            continue

        for k2, v2 in v1["properties"].items():
            if k2 != "network":
                continue
            if not isinstance(v2, dict):
                invalid_get_param.append(k1)
            elif "get_resource" in v2:
                if not v2["get_resource"].startswith("int_"):
                    invalid_get_resource.append(k1)
            elif "get_param" not in v2:
                invalid_get_param.append(k1)
    # TODO:  I don't think this test needs to check get_param as that is
    #        already covered by another test.

    msg = (
        "A OS::Neutron::Port must connect to an internal network using "
        "get_resource (network created in same template) or get_param "
        "(network created in a different template)."
    )
    if invalid_get_resource:
        msg = (
            msg
            + "  These resources use get_resource to connect to a "
            + "non-internal network: {}"
        ).format(", ".join(invalid_get_resource))
    if invalid_get_param:
        msg = (
            msg
            + "  These resources do not use get_resource or get_param "
            + "to connect to a network: {}"
        ).format(", ".join(invalid_get_param))

    assert not (invalid_get_param or invalid_get_resource), msg
