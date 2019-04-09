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
import re

from tests.helpers import validates, check_indices
from tests.structures import Heat
from tests.utils import nested_dict


IP_PARAM_PATTERN = re.compile(r"^(.*_ip_)(\d+)$")


@validates("R-71577", "R-40971")
def test_ips_start_at_0(yaml_file):
    heat = Heat(filepath=yaml_file)
    ports = heat.get_resource_by_type("OS::Neutron::Port")
    ip_parameters = []

    for rid, resource in ports.items():
        fips = nested_dict.get(resource, "properties", "fixed_ips", default={})
        for fip in fips:
            ip_address = fip.get("ip_address", {})
            param = ip_address.get("get_param")
            if isinstance(param, list):
                param = param[0]
            if isinstance(param, str):
                ip_parameters.append(param)

    invalid_params = check_indices(IP_PARAM_PATTERN, ip_parameters, "IP Parameters")
    assert not invalid_params, ". ".join(invalid_params)
