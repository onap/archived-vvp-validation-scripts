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

"""
test nesting level
0 -> 1 -> 2 -> too many levels.
"""

import pytest

from .utils import nested_files
from .helpers import validates

VERSION = "1.0.0"


def get_nova_server_count(heat):
    """return the number of OS::Nova::Server
    resources in heat
    """
    return len(heat.get_resource_by_type("OS::Nova::Server"))


# pylint: disable=invalid-name


@validates("R-17528")
def test_nesting_nova_server(yaml_files):
    """
    A VNF's Heat Orchestration Template's first level Nested YAML file
    **MUST NOT** contain more than one ``OS::Nova::Server`` resource.
    A VNF's Heat Orchestration Template's second level Nested YAML file
    **MUST NOT** contain an ``OS::Nova::Server`` resource.

    level: 0    1         2         3
    template -> nested -> nested -> too many levels
    """
    bad, __, heat, depths = nested_files.get_nesting(yaml_files)
    if bad:
        pytest.skip("nesting depth exceeded")
    for parent, depth in depths.items():
        for depth_tuple in depth:
            depth, context = depth_tuple
            if depth > 1:
                fname = context[0]
                nservers = get_nova_server_count(heat[fname])
                if nservers > 1:
                    bad.append(
                        "nested template %s must have only have 1 "
                        "OS::Nova::Server defined, but %s were found"
                        % (fname, nservers)
                    )
            if depth > 2:
                fname = context[1]
                nservers = get_nova_server_count(heat[fname])
                if nservers > 0:
                    bad.append(
                        "nested template %s must not have an "
                        "OS::Nova::Server defined, but %s were found"
                        % (fname, nservers)
                    )
    assert not bad, "; ".join(bad)
