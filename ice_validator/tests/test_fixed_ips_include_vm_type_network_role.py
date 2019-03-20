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

import re

from .helpers import validates
from .utils.ports import check_ip_format


RE_EXTERNAL_PARAM_FIP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+[^(v6)])(_v6)?_ip_(?P<ip_index>.+)$"
)

RE_EXTERNAL_PARAM_FIPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+[^(v6)])(_v6)?_ips$"
)

RE_INTERNAL_PARAM_FIP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+[^(v6)])(_v6)?_ip_(?P<ip_index>.+)$"
)

RE_INTERNAL_PARAM_FIPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+[^(v6)])(_v6)?_ips$"
)

fip_regx_dict = {
    "external": {
        "string": {
            "readable": "{vm-type}_{network-role}_ip_{ip-index} or {vm-type}_{network-role}_v6_ip_{ip-index}",
            "machine": RE_EXTERNAL_PARAM_FIP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_{network-role}_ips or {vm-type}_{network-role}_v6_ips",
            "machine": RE_EXTERNAL_PARAM_FIPS,
        },
    },
    "internal": {
        "string": {
            "readable": "{vm-type}_int_{network-role}_ip_{ip-index} or {vm-type}_int_{network-role}_v6_ip_{ip-index}",
            "machine": RE_INTERNAL_PARAM_FIP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_int_{network-role}_ips or {vm-type}_int_{network-role}_v6_ips",
            "machine": RE_INTERNAL_PARAM_FIPS,
        },
    },
    "parameter_to_resource_comparisons": ["vm_type", "network_role"],
}


@validates("R-40971", "R-35735", "R-23503", "R-71577", "R-04697", "R-34037")
def test_external_fip_format(yaml_file):
    check_ip_format(yaml_file, fip_regx_dict, "external", "fixed_ips", "ip_address")


@validates("R-27818", "R-29765", "R-85235", "R-78380", "R-34037")
def test_internal_fip_format(yaml_file):
    check_ip_format(yaml_file, fip_regx_dict, "internal", "fixed_ips", "ip_address")
