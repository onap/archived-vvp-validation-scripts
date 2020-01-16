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

from .structures import Heat
from .utils import nested_files
from .helpers import validates


@validates("R-60011", "R-17528")
def test_nesting_level(yaml_files):
    errors = set()
    non_nested_files = [
        f for f in yaml_files if not nested_files.file_is_a_nested_template(f)
    ]
    heats = [Heat(f) for f in non_nested_files]
    for heat in heats:
        for depth, nested_heat in heat.iter_nested_heat():
            if depth >= 3:
                errors.add(
                    (
                        "{} is nested {} levels deep, but a maximum of {} levels are "
                        "supported."
                    ).format(nested_heat.basename, depth, nested_files.MAX_DEPTH)
                )
            if depth == 2 and nested_heat.resources:
                errors.add(
                    (
                        "{} is a second level nested file, but it includes "
                        "resources. Remove all Heat resources from this file."
                    ).format(nested_heat.basename)
                )
    assert not errors, "\n\n".join(errors)
