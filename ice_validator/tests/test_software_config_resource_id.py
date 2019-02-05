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
resources:
{vm-type}_{vm-type_index}_{network-role}_port_{port-index}:
"""

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"

# pylint: disable=invalid-name


@validates("R-08975")
def test_software_config_vm_type(yaml_file):
    """
    A VNF's Heat Orchestration Template's Resource OS::Heat::SoftwareConfig
    Resource ID **MUST** contain the {vm-type}.
    """
    heat = Heat(filepath=yaml_file)
    software_configs = heat.get_resource_by_type("OS::Heat::SoftwareConfig")
    if not software_configs:
        pytest.skip("No SoftwareConfig resources found")
    vm_types = sorted(
        list(
            set(
                x
                for x in [
                    heat.get_vm_type(rid, resource=r)
                    for rid, r in heat.resources.items()
                ]
                if x
            )
        )
    )
    if not vm_types:
        pytest.skip("No vm_types found")
    bad = []
    for rid in software_configs:
        if not any(heat.part_is_in_name(part=v, name=rid) for v in vm_types):
            bad.append("%s vm-type not in %s" % (rid, vm_types))
    assert not bad, "; ".join(bad)
