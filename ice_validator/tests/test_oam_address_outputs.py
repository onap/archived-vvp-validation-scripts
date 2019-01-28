# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2019 AT&T Intellectual Property. All rights reserved.
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
import os

from tests.helpers import validates
from tests.structures import Heat

MSG = (
    "OAM management address can be declared as output in at most 1 template. "
    + "Output parameter {} found in multiple templates: {}"
)


def find_output_param(param, templates):
    templates = (t for t in templates if param in Heat(t).outputs)
    return [os.path.basename(t) for t in templates]


@validates("R-18683")
def test_oam_address_v4_zero_or_one(heat_templates):
    param = "oam_management_v4_address"
    templates = find_output_param(param, heat_templates)
    assert len(templates) <= 1, MSG.format(param, ", ".join(templates))


@validates("R-94669")
def test_oam_address_v6_zero_or_one(heat_templates):
    param = "oam_management_v6_address"
    templates = find_output_param(param, heat_templates)
    assert len(templates) <= 1, MSG.format(param, ", ".join(templates))
