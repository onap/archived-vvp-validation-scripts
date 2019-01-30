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

"""heat parameters
"""

import collections

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.0.0"


@validates("R-10834")
def test_nested_parameter_args(heat_template):
    """
    If a VNF’s Heat Orchestration Template resource attribute
    property metadata uses a nested get_param, then the "outer"
    get_param must take 2 arguments.  The first argument must be
    a parameter of type "comma_delimited_list", and the second
    argument must be the "inner" get_param whose value must be a
    parameter of type "number".

    parameters:
        cdl:
            type: comma_delimited_list
        num:
            type: number
    resources:
        ex1_nova_server_0:
            type: OS::Nova::Server
            properties:
                name: { get_param: [ ex1_vm_names, 0 ] }
                metadata:
                    vnf_id: { get_param: vnf_id }
                    vf_module_id:
                        get_param: [ cdl, { get_param: num }]
    """
    heat = Heat(filepath=heat_template)
    if not heat.resources:
        pytest.skip("No resources found")
    has_nested_parameters = False
    bad = collections.defaultdict(list)
    for rid, r in heat.resources.items():
        metadata = heat.nested_get(r, "properties", "metadata", default={})
        for key, value in metadata.items():
            param = heat.nested_get(value, "get_param")
            if isinstance(param, list) and len(param) == 2:
                nested_param = heat.nested_get(param[1], "get_param")
                if nested_param:
                    has_nested_parameters = True
                    if (
                        heat.nested_get(heat.parameters, param[0], "type")
                        != Heat.type_cdl
                    ):
                        bad[rid].append(
                            "%s %s parameter type not %s"
                            % (key, param[0], Heat.type_cdl)
                        )
                    if (
                        heat.nested_get(heat.parameters, nested_param, "type")
                        != Heat.type_num
                    ):
                        bad[rid].append(
                            "%s %s nested parameter type not %s"
                            % (key, nested_param, Heat.type_num)
                        )
    assert not bad, "resource ids with invalid nested parameter arguments\n    %s" % (
        "\n    ".join("%s %s" % (k, ", ".join(v)) for k, v in bad.items())
    )
    if has_nested_parameters is False:
        pytest.skip("No nested parameters found")
