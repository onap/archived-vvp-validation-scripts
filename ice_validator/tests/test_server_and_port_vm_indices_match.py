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
import re

from tests.helpers import validates
from tests.structures import Heat
from tests.utils import nested_dict

SERVER_ID_PATTERN = re.compile(r"\w+_server_(\d+)")
PORT_ID_PATTERN = re.compile(r"\w+_(\d+)_\w+\d+")


def get_ports(server):
    props = server.get("properties") or {}
    networks = props.get("networks") or []
    for network in networks:
        r_id = nested_dict.get(network, "port", "get_resource")
        if r_id:
            yield r_id


@validates("R-304011")
def test_server_and_port_vmtype_indices_match(yaml_file):
    # NOTE: This test is only going to validate that the index values
    # match between the between the ports and server names.  Other
    # tests already cover the other aspects of this requirement

    heat = Heat(filepath=yaml_file)
    servers = heat.get_resource_by_type("OS::Nova::Server")
    errors = []
    for r_id, server in servers.items():
        match = SERVER_ID_PATTERN.match(r_id)
        if not match:
            continue  # other tests cover valid server ID format
        server_index = match.group(1)
        ports = get_ports(server)
        for port in ports:
            port_match = PORT_ID_PATTERN.match(port)
            if port_match:
                port_vm_index = port_match.group(1)
                if port_vm_index != server_index:
                    errors.append(
                        (
                            "{{vm-type_index}} ({}) in port ID ({}) "
                            + "does not match the {{index}} ({}) in the "
                            + "servers resource ID ({})"
                        ).format(port_vm_index, port, server_index, r_id)
                    )
    assert not errors, ". ".join(errors)
