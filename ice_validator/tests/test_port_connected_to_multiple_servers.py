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
from collections import defaultdict

import pytest

from tests.helpers import validates
from tests.structures import Heat, Resource


@validates("R-92635")
def test_port_connected_to_multiple_servers(yaml_file):
    """
    SDC will throw an error if a single port is connected to more than
    one server.  This test detects that condition and logs a test failure.
    """
    heat = Heat(yaml_file)
    if not heat.resources:
        pytest.skip("No resources")

    port_to_server = defaultdict(list)
    for server_id, server_data in heat.get_resource_by_type("OS::Nova::Server").items():
        server = Resource(server_id, server_data)
        ports = server.properties.get("networks", [])
        for port in ports:
            port_val = port.get("port")
            if isinstance(port_val, dict) and "get_resource" in port_val:
                port_id = port_val["get_resource"]
                port_to_server[port_id].append(server_id)
    errors = []
    for port, servers in port_to_server.items():
        if len(servers) > 1:
            errors.append("Port {} is connected to {}".format(port, ", ".join(servers)))
    msg = "A port cannot be connected to more than 1 server: {}".format(
        ". ".join(errors)
    )
    assert not errors, msg
