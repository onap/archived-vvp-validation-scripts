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
from .utils.nested_iterables import find_all_get_resource_in_yml


def test_volume_templates_outputs_match_resources(volume_template):
    '''
    Check that all referenced resources in the outputs of a volume
    template actually exists
    '''
    with open(volume_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the volume template")

    # skip if outputs are not defined
    if "outputs" not in yml:
        pytest.skip("No outputs specified in the volume template")

    referenced_resources = find_all_get_resource_in_yml(yml['outputs'])

    invalid_get_attr = []
    for k, v in yml['outputs'].items():
        if 'value' not in v:
            continue
        if 'get_attr' not in v['value']:
            continue
        if not isinstance(v['value']['get_attr'], list):
            continue

        for v1 in v['value']['get_attr']:
            if v1 in yml['resources']:
                break
        else:
            invalid_get_attr.append(k)

    assert (set(referenced_resources) <= set(yml["resources"]) and
            not invalid_get_attr)
