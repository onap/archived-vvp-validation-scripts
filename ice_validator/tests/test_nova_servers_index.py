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
Ensure that if a resource_id has an {index}, then all resources of
the same vm-type have an index, the indices are consecutive and start
with 0.
'''

import collections
import re

import pytest

from .structures import Heat
from .helpers import validates
from .utils import vm_types

VERSION = '1.1.0'

RE_INDEXED_RESOURCE_ID = re.compile(r'\w+_(?P<index>\d+)$')


@validates('R-11690')
def test_indices(heat_templates):
    '''validate indices
    '''
    indexed_resource_ids = {}
    resources = {}
    for heat_template in heat_templates:
        h = Heat(filepath=heat_template)
        if h.resources:
            indexed_resource_ids.update(get_indexed_resource_ids(h.resources))
            resources.update(h.resources)
    if not resources:
        pytest.skip('No resources found')

    if not indexed_resource_ids:
        pytest.skip('No resources with {index} found')

    types = get_types(resources, indexed_resource_ids)
    if not types:
        pytest.skip('No resources with {vm-type} found')

    indices = collections.defaultdict(list)
    for resource_id, vm_type in types.items():
        indices[vm_type].append(indexed_resource_ids[resource_id])
    bad = {}
    for vm_type, index_list in indices.items():
        for i in range(len(index_list)):
            if i not in index_list:
                bad[vm_type] = index_list
                break
    assert not bad, (
            'vm-type indices must be consecutive, unique,'
            ' and start at 0.\n    %s' % (
                    '\n    '.join(['Resource ID %s: VM Type: %s' % (x, y)
                                   for x, y in types.items() if y in bad])))


def get_indexed_resource_ids(resources):
    """Return dict. keys are resource_ids which end in an index.
    values are the integer index parsed from the resource_id.
    """
    indexed_resource_ids = {}
    for resource in resources:
        match = RE_INDEXED_RESOURCE_ID.match(resource)
        if match:
            indexed_resource_ids[resource] = int(match.groupdict()['index'])
    return indexed_resource_ids


def get_types(resources, indexed_resource_ids):
    """Return dict. keys are resource_ids from indexed_resource_ids.
    values are the vm-type extracted from the resource.
    """
    all_vm_types = {}
    for rid in indexed_resource_ids:
        x = vm_types.get_vm_types_for_resource(resources[rid])
        if x and len(x) == 1:
            all_vm_types[rid] = list(x)[0]  # x is a set.
    return all_vm_types
