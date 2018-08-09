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

'''
A VNF's Heat Orchestration Template's Resource ``OS::Heat::MultipartMime``
Resource ID **MUST** contain the ``{vm-type}``.
'''

import pytest

from .structures import Heat
from .helpers import validates
from .utils import vm_types

VERSION = '1.0.1'


@validates('R-30804')
def test_multipart_mime(heat_template):
    '''validate resource ids
    '''
    h = Heat(filepath=heat_template)
    if not h.resources:
        pytest.skip('No resources in this template')

    multipart_mimes = get_multipart_mimes(h)
    if not multipart_mimes:
        pytest.skip('No MultipartMime resources in this template')

    resource_vm_types = vm_types.get_vm_types(h.resources)
    if not resource_vm_types:
        pytest.skip('No resources with {vm-type} in this template')

    bad = set()
    for rid in multipart_mimes:
        for vm_type in resource_vm_types:
            if vm_type in rid:
                break
        else:
            bad.add(rid)
    assert not bad, 'MultipartMime %s have {vm-type} not in %s' % (
            list(bad),
            list(resource_vm_types))


def get_multipart_mimes(heat):
    """Return list of resource_id whose type is OS::Heat::MultipartMime.
    """
    return [rid for rid, resource in heat.resources.items()
            if heat.nested_get(resource, 'type') == 'OS::Heat::MultipartMime']
