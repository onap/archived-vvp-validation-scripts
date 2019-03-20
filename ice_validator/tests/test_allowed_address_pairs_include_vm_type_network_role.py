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
#
import pytest
import re
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.ports import check_ip_format

VERSION = "1.0.0"

# pylint: disable=invalid-name

RE_EXTERNAL_PARAM_AAP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+)_floating(_v6)?_ip$"
)

RE_INTERNAL_PARAM_AAP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+)_floating(_v6)?_ip$"
)

RE_INTERNAL_PARAM_AAPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+)_floating(_v6)?_ips$"
)

aap_regx_dict = {
    "external": {
        "string": {
            "readable": "{vm-type}_{network-role}_floating_ip or {vm-type}_{network-role}_floating_v6_ip",
            "machine": RE_EXTERNAL_PARAM_AAP,
        }
    },
    "internal": {
        "string": {
            "readable": "{vm-type}_int_{network-role}_floating_ip or {vm-type}_int_{network-role}_floating_v6_ip",
            "machine": RE_INTERNAL_PARAM_AAP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_int_{network-role}_floating_ips or {vm-type}_int_{network-role}_floating_v6_ips",
            "machine": RE_INTERNAL_PARAM_AAPS,
        },
    },
    "parameter_to_resource_comparisons": ["vm_type", "network_role"],
}


@validates("R-41492", "R-35735", "R-159016")
def test_external_aap_format(yaml_file):
    check_ip_format(
        yaml_file, aap_regx_dict, "external", "allowed_address_pairs", "ip_address"
    )


@validates("R-717227", "R-805572")
def test_internal_aap_format(yaml_file):
    check_ip_format(
        yaml_file, aap_regx_dict, "internal", "allowed_address_pairs", "ip_address"
    )
