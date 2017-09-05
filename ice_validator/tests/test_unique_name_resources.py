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

import yaml
import pytest


def test_unique_name_resources(yaml_files):
    '''
    Check that all resource names are unique across all yaml files.
    The specifics of str_replace naming is carried out in a
    different test
    '''
    resource_names = []

    params_using_index = {}

    for yaml_file in yaml_files:
        with open(yaml_file) as fh:
            yml = yaml.load(fh)

        # skip if resources are not defined
        if "resources" not in yml:
            continue

        for v1 in yml["resources"].values():
            if not isinstance(v1, dict):
                continue
            if "properties" not in v1:
                continue

            try:
                v2 = v1["properties"]["name"]
            except (TypeError, KeyError):
                continue

            try:
                param = v2["get_param"]
            except (TypeError, KeyError):
                param = None

            if param:
                if isinstance(param, list):
                    name = param[0]
                    index = param[1]

                    if (isinstance(index, dict) and
                       'get_param' in index):
                        get_param = index['get_param']

                        if name not in params_using_index:
                            params_using_index[name] = get_param
                            param = name + get_param
                        else:
                            continue
                    else:
                        param = name + str(index)

                resource_names.append(param)
            else:
                try:
                    template = v2["str_replace"]["yaml_file"]
                    resource_names.append(template)
                except (TypeError, KeyError):
                    continue

    if not resource_names:
        pytest.skip("No resource names could be detected")

    assert len(resource_names) == len(set(resource_names))
