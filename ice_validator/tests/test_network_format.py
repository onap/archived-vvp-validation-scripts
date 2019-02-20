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
import re

from tests import cached_yaml as yaml

from .helpers import validates
from .utils.network_roles import get_network_role_from_port, property_uses_get_resource

RE_INTERNAL_NETWORK_RID = re.compile(  # match pattern
    r"int_(?P<network_role>.+)_network$"
)
NETWORK_RESOURCE_TYPES = ["OS::Neutron::Net", "OS::ContrailV2::VirtualNetwork"]


@validates("R-62983", "R-86182")
def test_network_format(yaml_file):
    """
    Make sure all network properties use the allowed naming
    conventions
    """
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_ports = []
    for k, v in yml["resources"].items():
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        if property_uses_get_resource(v, "network"):
            continue
        if v.get("type") != "OS::Neutron::Port":
            continue
        if not get_network_role_from_port(v):
            invalid_ports.append(k)

    assert not set(invalid_ports), (
        "Missing 'network' property or improperly "
        "formatted network parameter name on the "
        "following OS::Neutron::Ports: "
        "{}".format(", ".join(invalid_ports))
    )


@validates("R-16968", "R-35666")
def test_network_resource_id_format(yaml_file):
    """
    Make sure all network resource ids use the allowed naming
    convention
    """
    RE_INTERNAL_NETWORK_RID = re.compile(  # match pattern
        r"int_(?P<network_role>.+)_network$"
    )

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_networks = []
    for k, v in yml["resources"].items():
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        if property_uses_get_resource(v, "network"):
            continue
        if v.get("type") not in NETWORK_RESOURCE_TYPES:
            continue
        match = RE_INTERNAL_NETWORK_RID.match(k)
        if not match:
            invalid_networks.append(k)

    assert not set(invalid_networks), (
        "Heat templates must only create internal networks "
        "and follow format int_{{network-role}}_network"
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
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        # need to check if contrail networks also require subnet
        # and it is defined the same as neutron networks
        # if v.get("type") not in NETWORK_RESOURCE_TYPES:
        if v.get("type") not in ["OS::Neutron::Net"]:
            continue
        networks.append(k)

    for k, v in yml["resources"].items():
        if not isinstance(v, dict):
            continue
        if "properties" not in v:
            continue
        if v.get("type") != "OS::Neutron::Subnet":
            continue
        network_prop = v.get("properties", {}).get("network", {}).get("get_resource")

        if not network_prop:
            continue
        x = 0
        for network in networks:
            if network == network_prop:
                networks.pop(x)
                break
            x += 1

    assert not networks, "Networks detected without subnet {}".format(networks)
