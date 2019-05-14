# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
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
#

"""
OS::Neutron::Port connecting to external network
must have at most one ip_address and at most one v6_ip_address.
"""

import collections
import os.path

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"


def get_neutron_ports(heat):
    """Return dict of resource_id: resource, whose type is
    OS::Neutron::Port.
    """
    return {
        rid: resource
        for rid, resource in heat.resources.items()
        if heat.nested_get(resource, "type") == "OS::Neutron::Port"
    }


def get_port_addresses(filepath):
    """Return dict:
    key is field name, value is dict:
        key is parameter name, value is dict:
            key is filepath, value is set of rid
    """
    port_addresses = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(set))
    )
    heat = Heat(filepath=filepath)
    basename = os.path.basename(filepath)
    for rid, port in get_neutron_ports(heat).items():
        allowed_address_pairs = heat.nested_get(
            port, "properties", "allowed_address_pairs"
        )
        if not isinstance(allowed_address_pairs, list):
            continue
        field = "ip_address"
        for aa_pair in allowed_address_pairs:
            param = heat.nested_get(aa_pair, field, "get_param")
            if param is None:
                continue
            else:
                param = param[0] if isinstance(param, list) else param
            port_addresses[field][param][basename].add(rid)
    return port_addresses


def nested_update(out_dict, in_dict):
    """Recursively update out_dict from in_dict.
    """
    for key, value in in_dict.items():
        if key not in out_dict:
            out_dict[key] = value
        elif isinstance(value, dict) and isinstance(out_dict[key], dict):
            out_dict[key] = nested_update(out_dict[key], value)
        elif isinstance(value, set) and isinstance(out_dict[key], set):
            out_dict[key].update(value)
        else:
            out_dict[key] = value
    return out_dict


@validates("R-10754")
def test_neutron_port_floating(yaml_files):
    """
    If a VNF has two or more ports that
    attach to an external network that require a Virtual IP Address (VIP),
    and the VNF requires ONAP automation to assign the IP address,
    all the Virtual Machines using the VIP address **MUST**
    be instantiated in the same Base Module Heat Orchestration Template
    or in the same Incremental Module Heat Orchestration Template.
    """
    fields = {}
    for filepath in yaml_files:
        fields = nested_update(fields, get_port_addresses(filepath))
    bad = []
    for field, params in fields.items():
        for param, files in params.items():
            if len(files) > 1:
                error = ["{} {} assigned in multiple templates: ".format(field, param)]
                for file_name, r_ids in files.items():
                    error.append(
                        "In {} it's assigned to {}. ".format(
                            file_name, ", ".join(r_ids)
                        )
                    )
                bad.append("".join(error))
    assert not bad, "; ".join(bad)
