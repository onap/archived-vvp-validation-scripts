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

"""
resources:
{vm-type}_server_{vm-type_index}
"""
import pytest

from .structures import Heat
from .structures import NovaServer
from .helpers import validates

VERSION = "1.0.0"

# pylint: disable=invalid-name


@validates("R-29751")
def test_nova_server_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    OS::Nova::Server Resource ID
    **MUST** use the naming convention

    * ``{vm-type}_server_{index}``

    """
    heat = Heat(filepath=heat_template)
    resources = heat.nova_server_resources
    if not resources:
        pytest.skip("No Nova Server resources found")
    nova_server = NovaServer()
    bad = []
    for rid in resources:
        if not nova_server.get_rid_match_tuple(rid)[0]:
            bad.append(rid)
    assert not bad, "Resource ids %s must match %s" % (
        bad,
        nova_server.get_rid_patterns(),
    )
