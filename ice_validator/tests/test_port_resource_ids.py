# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the “License”);
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
# under the Creative Commons License, Attribution 4.0 Intl. (the “License”);
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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

import re
import pytest
import yaml
from .utils.vm_types import get_vm_type_for_nova_server
from .utils.network_roles import get_network_role_from_port,\
                                 get_network_type_from_port


def test_port_resource_ids(heat_template):
    '''
    Check that all resource ids for ports follow the right
    naming convention to include the {vm_type} of the
    nova server it is associated to and also contains the
    {network_role} of the network it is associated with
    '''
    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    port_patterns = {
                    'internal': re.compile(r'(.+?)_\d+_int_(.+?)_\d+_port'),
                    'external': re.compile(r'(.+?)_\d+_(.+?)_\d+_port'),
                    }
    resources = yml['resources']

    invalid_ports = []
    for k, v in resources.items():
        if not isinstance(v, dict):
            continue
        if 'type' not in v:
            continue
        if v['type'] not in 'OS::Nova::Server':
            continue
        if 'properties' not in v:
            continue
        if 'networks' not in v['properties']:
            continue

        has_vm_type = False
        has_network_role = True
        port_resource = None

        vm_type = get_vm_type_for_nova_server(v)
        if not vm_type:
            continue
        vm_type = vm_type.lower()

        # get all ports associated with the nova server
        properties = v['properties']
        for v2 in properties['networks']:
            for k3, v3 in v2.items():
                if k3 != 'port':
                    continue
                if not isinstance(v3, dict):
                    continue

                if 'get_param' in v3:
                    continue
                elif 'get_resource' in v3:
                    port_id = v3['get_resource']
                    if not resources[port_id]:
                        continue
                    port_resource = resources[port_id]
                    port_id = port_id.lower()
                else:
                    continue

                has_vm_type = vm_type+"_" in port_id

                if port_resource:
                    network_role = get_network_role_from_port(port_resource)
                    if not network_role:
                        continue
                    network_role = network_role.lower()

                    network_type = get_network_type_from_port(port_resource)
                    if not network_type:
                        continue

                    prepend = ""
                    if network_type == 'internal':
                        prepend = "int_"
                    has_network_role = prepend+network_role+"_" in port_id
                else:
                    # match the assumed naming convention for ports
                    # if the specified port is provided via get_param
                    network_type = 'external'
                    if "int_" in port_id:
                        network_type = 'internal'
                    if port_patterns[network_type].match(port_id):
                        has_network_role = True

                if has_vm_type and has_network_role:
                    continue
                invalid_ports.append(port_id)

    assert not set(invalid_ports)
