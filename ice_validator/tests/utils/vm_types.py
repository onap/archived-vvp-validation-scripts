# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the “License”);
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
# under the Creative Commons License, Attribution 4.0 Intl. (the “License”);
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

import re


def get_vm_types_for_resource(resource):
    '''
    Get all unique vm_types for a resource
    Notes:
    - Returns set([]) if the resource is not formatted
    properly, the passed resource is not a nova server
    - If more than one vm_type is detected all vm_types will
    be returned
    '''
    if not isinstance(resource, dict):
        return set()
    if 'type' not in resource:
        return set()
    if resource['type'] != 'OS::Nova::Server':
        return set()
    if 'properties' not in resource:
        return set()

    key_values = ["name", "flavor", "image"]
    key_value_formats = [
                        ["name", "string",
                         re.compile(r'(.+?)_name_\d+')],
                        ["name", "comma_delimited_list",
                         re.compile(r'(.+?)_names')],
                        ["flavor", "string",
                         re.compile(r'(.+?)_flavor_name')],
                        ["image", "string",
                         re.compile(r'(.+?)_image_name')],
                        ]

    vm_types = []
    for k2, v2 in resource['properties'].items():
        if k2 not in key_values:
            continue
        if "get_param" not in v2:
            continue
        formats = [v for v in key_value_formats if v[0] == k2]
        for v3 in formats:
            param = v2["get_param"]
            if isinstance(param, list):
                param = param[0]
            m = v3[2].match(param)
            if m and m.group(1):
                vm_types.append(m.group(1))

    return set(vm_types)


def get_vm_type_for_nova_server(resource):
    '''
    Get the vm_type for a resource
    Note: Returns None if not exactly one vm_type
    is detected, if the resource is not formatted properly, or
    the passed resource is not a nova server
    '''
    vm_types = get_vm_types_for_resource(resource)

    # if more than one vm_type was identified, return None
    if len(vm_types) > 1:
        return None

    return vm_types.pop()


def get_vm_types(resources):
    '''
    Get all vm_types for a list of heat resources, do note that
    some of the values retrieved may be invalid
    '''
    vm_types = []
    for v in resources.values():
        vm_types.extend(list(get_vm_types_for_resource(v)))

    return set(vm_types)
