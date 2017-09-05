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

from .network_roles import get_network_role_from_port
from .vm_types import get_vm_type_for_nova_server
import re


def is_valid_ip_address(ip_address, vm_type, network_role, port_property):
    '''
    Check the ip_address to make sure it is properly formatted and
    also contains {vm_type} and {network_role}
    '''

    allowed_formats = [
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_floating_v6_ip')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_floating_ip')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_floating_v6_ip')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_floating_ip')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_v6_ip_\d+')],
                      ["allowed_address_pairs", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_ip_\d+')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_v6_ip_\d+')],
                      ["allowed_address_pairs", "string", "external",
                       re.compile(r'(.+?)_ip_\d+')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "internal", re.compile(r'(.+?)_int_(.+?)_v6_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "internal", re.compile(r'(.+?)_int_(.+?)_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "external", re.compile(r'(.+?)_v6_ips')],
                      ["allowed_address_pairs", "comma_delimited_list",
                       "external", re.compile(r'(.+?)_ips')],
                      ["fixed_ips", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_v6_ip_\d+')],
                      ["fixed_ips", "string", "internal",
                       re.compile(r'(.+?)_int_(.+?)_ip_\d+')],
                      ["fixed_ips", "string", "external",
                       re.compile(r'(.+?)_v6_ip_\d+')],
                      ["fixed_ips", "string", "external",
                       re.compile(r'(.+?)_ip_\d+')],
                      ["fixed_ips", "comma_delimited_list", "internal",
                       re.compile(r'(.+?)_int_(.+?)_v6_ips')],
                      ["fixed_ips", "comma_delimited_list", "internal",
                       re.compile(r'(.+?)_int_(.+?)_ips')],
                      ["fixed_ips", "comma_delimited_list", "external",
                       re.compile(r'(.+?)_v6_ips')],
                      ["fixed_ips", "comma_delimited_list", "external",
                       re.compile(r'(.+?)_ips')],
                      ]

    for v3 in allowed_formats:
        if v3[0] != port_property:
            continue
        # check if pattern matches
        m = v3[3].match(ip_address)
        if m:
            if (v3[2] == "internal" and
                    len(m.groups()) > 1):
                    return m.group(1) == vm_type and\
                        m.group(2) == network_role
            elif (v3[2] == "external" and
                  len(m.groups()) > 0):
                return m.group(1) == vm_type + "_" + network_role

    return False


def get_invalid_ip_addresses(resources, port_property):
    '''
    Get a list of valid ip addresses for a heat resources section
    '''
    invalid_ip_addresses = []

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

        port_resource = None

        vm_type = get_vm_type_for_nova_server(v)
        if not vm_type:
            continue

        # get all ports associated with the nova server
        properties = v['properties']
        for network in properties['networks']:
            for k3, v3 in network.items():
                if k3 != 'port':
                    continue
                if not isinstance(v3, dict):
                    continue

                if 'get_resource' in v3:
                    port_id = v3['get_resource']
                    if not resources[port_id]:
                        continue
                    port_resource = resources[port_id]
                else:
                    continue

                network_role = get_network_role_from_port(port_resource)
                if not network_role:
                    continue

                for k1, v1 in port_resource["properties"].items():
                    if k1 != port_property:
                        continue
                    for v2 in v1:
                        if "ip_address" not in v2:
                            continue
                        if "get_param" not in v2["ip_address"]:
                            continue

                        ip_address = v2["ip_address"]["get_param"]

                        if isinstance(ip_address, list):
                            ip_address = ip_address[0]

                        valid_ip_address = is_valid_ip_address(ip_address,
                                                               vm_type,
                                                               network_role,
                                                               port_property)

                        if not valid_ip_address:
                            invalid_ip_addresses.append(ip_address)

    return invalid_ip_addresses
