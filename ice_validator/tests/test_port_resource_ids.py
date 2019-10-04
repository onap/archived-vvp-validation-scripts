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
#

import re

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.network_roles import (
    get_network_role_from_port,
    get_network_type_from_port,
    property_uses_get_resource,
)
from .utils.vm_types import get_vm_type_for_nova_server


@validates("R-20453", "R-26351", "R-26506", "R-681859")
def test_port_resource_ids(yaml_file):
    """
    Check that all resource ids for ports follow the right
    naming convention to include the {vm_type} of the
    nova server it is associated to and also contains the
    {network_role} of the network it is associated with
    """
    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    resources = yml["resources"]

    invalid_ports = []
    for k, v in resources.items():
        if any([not isinstance(v, dict), "type" not in v, v["type"] not in "OS::Nova::Server", "properties" not in v, "networks" not in v["properties"]]):
            continue
        vm_type = get_vm_type_for_nova_server(v)
        if not vm_type:
            continue
        vm_type = vm_type.lower()

        # get all ports associated with the nova server
        properties = v["properties"]
        for v2 in properties["networks"]:
            for k3, v3 in v2.items():
                if any([k3 != "port", not isinstance(v3, dict)]):
                    continue
                if "get_param" in v3:
                    continue
                elif "get_resource" in v3:
                    port_id = v3["get_resource"]
                    if not resources[port_id]:
                        continue
                    port_resource = resources[port_id]
                    port_id = port_id.lower()
                else:
                    continue

                if property_uses_get_resource(v, "network"):
                    continue
                network_role = get_network_role_from_port(port_resource)
                if not network_role:
                    continue
                network_role = network_role.lower()

                network_type = get_network_type_from_port(port_resource)
                if not network_type:
                    continue
                if network_type == "external":
                    expected_r_id = r"{}_\d+_{}_port_\d+".format(vm_type, network_role)
                else:
                    expected_r_id = r"{}_\d+_int_{}_port_\d+".format(
                        vm_type, network_role
                    )
                if not re.match(expected_r_id, port_id):
                    invalid_ports.append(
                        (port_id, "Did not match {}".format(expected_r_id))
                    )

    port_errors = "; ".join(
        "{} -> {}".format(port, error) for port, error in invalid_ports
    )
    msg = "The following ports have invalid resource IDs: {}".format(port_errors)
    msg = msg.replace(r"\d+", "{index}")
    assert not invalid_ports, msg
