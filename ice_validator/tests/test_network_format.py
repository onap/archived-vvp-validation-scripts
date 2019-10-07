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
from itertools import chain

import pytest
import re

from tests import cached_yaml as yaml
from tests.structures import Heat

from tests.helpers import validates

RE_INTERNAL_NETWORK_RID = re.compile(r"int_(?P<network_role>.+)_network$")
NETWORK_RESOURCE_TYPES = ["OS::Neutron::Net", "OS::ContrailV2::VirtualNetwork"]


@validates("R-16968")
def test_network_resource_id_format(yaml_file):
    heat = Heat(yaml_file)
    network_ids = chain.from_iterable(
        heat.get_resource_by_type(t) for t in NETWORK_RESOURCE_TYPES
    )
    invalid_networks = {
        r_id for r_id in network_ids if not RE_INTERNAL_NETWORK_RID.match(r_id)
    }
    assert not invalid_networks, (
        "Heat templates must only create internal networks "
        "and their resource IDs must follow the format "
        "int_{{network-role}}_network. The following network's resource IDs "
        "have invalid resource ID formats: "
        "{}".format(", ".join(invalid_networks))
    )


@validates("R-16241")
def test_network_has_subnet(yaml_file):
    """
    if creating internal network, make sure there is a
    corresponding subnet that references it
    """

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    networks = []

    for k, v in yml["resources"].items():
        if not has_properties(v) or v.get("type") not in ["OS::Neutron::Net"]:
            continue
        # need to check if contrail networks also require subnet
        # and it is defined the same as neutron networks
        # if v.get("type") not in NETWORK_RESOURCE_TYPES:
        networks.append(k)

    for k, v in yml["resources"].items():
        network_prop = v.get("properties", {}).get("network", {}).get("get_resource")
        if (
            not has_properties(v)
            and v.get("type") != "OS::Neutron::Subnet"
            and not network_prop
        ):
            continue
        x = 0
        for network in networks:
            if network == network_prop:
                networks.pop(x)
                break
            x += 1

    assert not networks, "Networks detected without subnet {}".format(networks)


def has_properties(resource):
    """
    checks resource is a Neutron Subnet
    """
    return isinstance(resource, dict) and "properties" in resource
