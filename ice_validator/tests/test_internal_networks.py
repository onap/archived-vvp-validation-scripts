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
import re
from itertools import chain

from tests.helpers import validates
from tests.structures import Heat
from tests.test_network_format import NETWORK_RESOURCE_TYPES, RE_INTERNAL_NETWORK_RID

INTERNAL_NETWORK_PARAMETERS = [
    re.compile(r"int_(.+?)_net_id"),
    re.compile(r"int_(.+?)_net_name"),
    re.compile(r".*_int_(.+?)_floating(?:_v6)?_ip"),
    re.compile(r".*_int_(.+?)_floating(?:_v6)?_ips"),
    re.compile(r".*?_int_(.+?)(?:_v6)?_ips"),
    re.compile(r".*?_int_(.+?)(?:_v6)?_ip_\d+"),
    re.compile(r"int_(.+?)(?:_v6)?_subnet_id"),
    re.compile(r"(?:.*_)?int_(.+?)_security_group"),
]


def get_network_ids(heat):
    return set(
        chain.from_iterable(
            heat.get_resource_by_type(t)
            for t in NETWORK_RESOURCE_TYPES
        )
    )


def get_internal_network_roles(heat_templates):
    network_ids = chain.from_iterable(get_network_ids(t) for t in heat_templates)
    matches = (RE_INTERNAL_NETWORK_RID.match(nid) for nid in network_ids)
    return {m.groupdict().get("network_role", "").lower() for m in matches if m}


def first_match(param, patterns):
    for pattern in patterns:
        match = pattern.match(param)
        if match:
            return match
    return None


@validates("R-35666")
def test_networks_exist_for_internal_network_params(yaml_files):
    heat_templates = [t for t in map(Heat, yaml_files) if t.is_heat]
    network_roles = get_internal_network_roles(heat_templates)
    errors = []
    for heat in heat_templates:
        for param in heat.parameters:
            match = first_match(param, INTERNAL_NETWORK_PARAMETERS)
            if not match:
                continue
            param_role = match.groups()[0]
            if param_role not in network_roles:
                errors.append((
                    "Parameter {} in template {} uses the internal network naming "
                    "convention, but no network with a resource ID of int_{}_network "
                    "was defined in any Heat template. Update the parameter to use "
                    "the naming convention for external networks or ensure the "
                    "internal network is defined in the VNF's Heat templates. Refer "
                    "to Networking section of Heat requirements for full definitions "
                    "of internal vs. external networks."
                ).format(param, heat.basename, param_role))

        assert not errors, "\n\n".join(errors)
