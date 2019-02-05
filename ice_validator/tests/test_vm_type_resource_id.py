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

"""vm-type resource_id
"""

import pytest

from .structures import Heat
from .helpers import validates
from .utils import vm_types as utils_vm_types

VERSION = "1.1.0"


@validates("R-46839")
def test_vm_type_resource_id(yaml_file):
    """
    A VNF's Heat Orchestration Template's use of ``{vm-type}``
    in all Resource IDs **MUST** be the same case.
    """
    bad = {}
    h = Heat(filepath=yaml_file)
    if not h.resources:
        pytest.skip("No resources specified in the heat template")
    vm_types = {
        v + "_": v.lower() + "_" for v in utils_vm_types.get_vm_types(h.resources)
    }
    if not vm_types:
        pytest.skip("No {vm-type} specified in the heat template")

    for rid in h.resources:
        lower_rid = rid.lower()
        for vm_type, lower_vm_type in vm_types.items():
            if lower_rid.startswith(lower_vm_type) and not rid.startswith(vm_type):
                bad[rid] = vm_type
    assert not bad, "resource_id which do not match their vm-type %s" % bad
