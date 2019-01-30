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
import pytest

from tests import cached_yaml as yaml
from .helpers import validates


@validates("R-89913")
def test_volume_templates_contains_outputs(volume_template):
    """
    Check that all volume templates include outputs
    """
    with open(volume_template) as fh:
        yml = yaml.load(fh)

    resources = yml.get("resources")
    volume_resources = []
    invalid_resource_ids = []
    output_resources = []

    if not resources:
        pytest.skip("No resources detected in template")

    for rid, rprop in resources.items():
        rtype = rprop.get("type")
        if not rtype:
            continue
        if rtype == "OS::Cinder::Volume":
            volume_resources.append(rid)

    outputs = yml.get("outputs")
    if not outputs:
        pytest.fail("No outputs detected in volume template")

    for k1, v1 in outputs.items():
        output_value = v1.get("value", {}).get("get_resource")
        if not output_value:
            continue
        output_resources.append(output_value)

    for rid in volume_resources:
        if rid not in output_resources:
            invalid_resource_ids.append(rid)

    assert (
        not invalid_resource_ids
    ), "volumes resource IDs not found in outputs of volume module {}".format(
        invalid_resource_ids
    )
