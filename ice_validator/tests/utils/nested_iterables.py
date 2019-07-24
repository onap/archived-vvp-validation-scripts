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
from tests.helpers import traverse


def is_pseudo_param(parameter):
    pseudo_parameters = ["OS::stack_name", "OS::stack_id", "OS::project_id"]
    return parameter in pseudo_parameters


class ParameterCollector:
    def __init__(self):
        self.params = set()

    def __call__(self, _, value):
        if isinstance(value, str):
            self.params.add(value)
        elif isinstance(value, list) and len(value) >= 1:
            self.params.add(value[0])


def find_all_get_param_in_yml(yml):
    """
    Recursively find all referenced parameters in a parsed yaml body
    and return a list of parameters
    """
    collector = ParameterCollector()
    traverse(yml, "get_param", collector)
    return {p for p in collector.params if not is_pseudo_param(p)}


def find_all_get_resource_in_yml(yml):
    """
    Recursively find all referenced resources
    in a parsed yaml body and return a list of resource ids
    """
    collector = ParameterCollector()
    traverse(yml, "get_resource", collector)
    return collector.params


def find_all_get_file_in_yml(yml):
    """
    Recursively find all get_file in a parsed yaml body
    and return the list of referenced files/urls
    """
    collector = ParameterCollector()
    traverse(yml, "get_file", collector)
    return collector.params
