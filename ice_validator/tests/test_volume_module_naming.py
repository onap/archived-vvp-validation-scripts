# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2018 AT&T Intellectual Property. All rights reserved.
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
import os

from tests.parametrizers import get_nested_files
from tests.structures import Heat, Resource


def non_nested_files(filenames):
    nested_files = get_nested_files(filenames)
    return set(filenames).difference(set(nested_files))


# No requirement ID yet available
def test_detected_volume_module_follows_naming_convention(template_dir):
    all_files = [os.path.join(template_dir, f) for f in os.listdir(template_dir)]
    yaml_files = [f for f in all_files if f.endswith(".yaml") or f.endswith(".yml")]
    errors = []
    for yaml_file in non_nested_files(yaml_files):
        heat = Heat(filepath=yaml_file)
        if not heat.resources:
            continue
        base_dir, filename = os.path.split(yaml_file)
        resources = heat.get_all_resources(base_dir)
        non_nested_ids = {
            r_id
            for r_id, r_data in resources.items()
            if not Resource(r_id, r_data).is_nested()
        }
        volume_ids = {
            r_id
            for r_id, r_data in resources.items()
            if Resource(r_id, r_data).resource_type == "OS::Cinder::Volume"
        }
        non_volume_ids = non_nested_ids.difference(volume_ids)
        if non_volume_ids:
            continue  # Not a volume module
        base_name, ext = os.path.splitext(filename)
        if not base_name.endswith("_volume") or ext not in (".yaml", ".yml"):
            errors.append(yaml_file)
        msg = (
            "Volume modules detected, but they do not follow the expected "
            + " naming convention {{module_name}}_volume.[yaml|yml]: {}"
        ).format(", ".join(errors))
        assert not errors, msg
