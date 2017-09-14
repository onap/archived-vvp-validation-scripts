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


def parse_nested_dict(d, key=""):
    '''
    parse the nested dictionary and return values of
    given key of function parameter only
    '''
    nested_elements = []
    for k, v in d.items():
        if isinstance(v, dict):
            sub_dict = parse_nested_dict(v, key)
            nested_elements.extend(sub_dict)
        else:
            if key:
                if k == key:
                    nested_elements.append(v)
            else:
                nested_elements.append(v)

    return nested_elements


def find_all_get_param_in_yml(yml):
    '''
    Recursively find all referenced parameters in a parsed yaml body
    and return a list of parameters
    '''
    os_pseudo_parameters = ['OS::stack_name',
                            'OS::stack_id',
                            'OS::project_id']

    if not hasattr(yml, 'items'):
        return []
    params = []
    for k, v in yml.items():
        if k == 'get_param' and v not in os_pseudo_parameters:
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, dict):
                    params.extend(find_all_get_param_in_yml(item))
                elif isinstance(item, str):
                    params.append(item)
            continue
        elif k == 'list_join':
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, list):
                    for d in item:
                        params.extend(find_all_get_param_in_yml(d))
            continue
        if isinstance(v, dict):
            params.extend(find_all_get_param_in_yml(v))
        elif isinstance(v, list):
            for d in v:
                params.extend(find_all_get_param_in_yml(d))
    return params


def find_all_get_resource_in_yml(yml):
    '''
    Recursively find all referenced resources
    in a parsed yaml body and return a list of resource ids
    '''
    if not hasattr(yml, 'items'):
        return []
    resources = []
    for k, v in yml.items():
        if k == 'get_resource':
            if isinstance(v, list):
                resources.append(v[0])
            else:
                resources.append(v)
            continue
        if isinstance(v, dict):
            resources.extend(find_all_get_resource_in_yml(v))
        elif isinstance(v, list):
            for d in v:
                resources.extend(find_all_get_resource_in_yml(d))
    return resources


def find_all_get_file_in_yml(yml):
    '''
    Recursively find all get_file in a parsed yaml body
    and return the list of referenced files/urls
    '''
    if not hasattr(yml, 'items'):
        return []
    resources = []
    for k, v in yml.items():
        if k == 'get_file':
            if isinstance(v, list):
                resources.append(v[0])
            else:
                resources.append(v)
            continue
        if isinstance(v, dict):
            resources.extend(find_all_get_file_in_yml(v))
        elif isinstance(v, list):
            for d in v:
                resources.extend(find_all_get_file_in_yml(d))
    return resources


def find_all_get_resource_in_resource(resource):
    '''
    Recursively find all referenced resources
    in a heat resource and return a list of resource ids
    '''
    if not hasattr(resource, 'items'):
        return []

    resources = []
    for k, v in resource.items():
        if k == 'get_resource':
            if isinstance(v, list):
                resources.append(v[0])
            else:
                resources.append(v)
            continue
        if isinstance(v, dict):
            resources.extend(
                find_all_get_resource_in_resource(v))
        elif isinstance(v, list):
            for d in v:
                resources.extend(
                    find_all_get_resource_in_resource(d))
    return resources


def get_associated_resources_per_resource(resources):
    '''
    Recursively find all referenced resources for each resource
    in a list of resource ids
    '''
    if not hasattr(resources, 'items'):
        return None

    resources_dict = {}
    resources_dict["resources"] = {}
    ref_resources = []

    for res_key, res_value in resources.items():
        get_resources = []

        for k, v in res_value:
            if k == 'get_resource' and\
               isinstance(v, dict):
                get_resources = find_all_get_resource_in_resource(v)

        # if resources found, add to dict
        if get_resources:
            ref_resources.extend(get_resources)
            resources_dict["resources"][res_key] = {
                "res_value": res_value,
                "get_resources": get_resources,
            }

    resources_dict["ref_resources"] = set(ref_resources)

    return resources_dict


def flatten(items):
    '''
    flatten items from any nested iterable
    '''

    merged_list = []
    for item in items:
        if isinstance(item, list):
            sub_list = flatten(item)
            merged_list.extend(sub_list)
        else:
            merged_list.append(item)
    return merged_list
