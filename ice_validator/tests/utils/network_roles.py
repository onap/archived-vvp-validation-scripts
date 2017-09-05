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
import socket


def get_network_role_from_port(resource):
    '''
    get the network role from a neutron port resource
    '''
    if not isinstance(resource, dict):
        return None
    if 'type' not in resource:
        return None
    if resource['type'] != 'OS::Neutron::Port':
        return None
    if 'properties' not in resource:
        return None

    formats = [
              ["network", "string", "internal",
               re.compile(r'int_(.+?)_net_id')],
              ["network", "string", "internal",
               re.compile(r'int_(.+?)_net_name')],
              ["network", "string", "external",
               re.compile(r'(.+?)_net_id')],
              ["network", "string", "external",
               re.compile(r'(.+?)_net_name')],
              ]

    for k1, v1 in resource["properties"].items():
        if k1 != 'network':
            continue

        # get the network id or name
        network = (
            v1.get('get_param') or
            v1.get('get_resource'))
        if not network:
            continue

        for v2 in formats:
            m = v2[3].match(network)
            if m and m.group(1):
                return m.group(1)

    return None


def get_network_type_from_port(resource):
    '''
    get the network type from a neutron port resource
    '''
    if not isinstance(resource, dict):
        return None
    if 'type' not in resource:
        return None
    if resource['type'] != 'OS::Neutron::Port':
        return None
    if 'properties' not in resource:
        return None

    formats = [
              ["network", "string", "internal",
               re.compile(r'int_(.+?)_net_id')],
              ["network", "string", "internal",
               re.compile(r'int_(.+?)_net_name')],
              ["network", "string", "external",
               re.compile(r'(.+?)_net_id')],
              ["network", "string", "external",
               re.compile(r'(.+?)_net_name')],
              ]

    for k1, v1 in resource["properties"].items():
        if k1 != 'network':
            continue
        if "get_param" not in v1:
            continue
        for v2 in formats:
            m = v2[3].match(v1["get_param"])
            if m and m.group(1):
                return v2[2]

    return None


def is_valid_ip_address(ip_address, ip_type='ipv4'):
    '''
    check if an ip address is valid
    '''
    if ip_type == 'ipv4':
        return is_valid_ipv4_address(ip_address)
    elif ip_type == 'ipv6':
        return is_valid_ipv6_address(ip_address)
    return False


def is_valid_ipv4_address(ip_address):
    '''
    check if an ip address of the type ipv4
    is valid
    '''
    try:
        socket.inet_pton(socket.AF_INET, ip_address)
    except AttributeError:
        try:
            socket.inet_aton(ip_address)
        except (OSError, socket.error):
            return False
        return ip_address.count('.') == 3
    except (OSError, socket.error):
        return False
    return True


def is_valid_ipv6_address(ip_address):
    '''
    check if an ip address of the type ipv6
    is valid
    '''
    try:
        socket.inet_pton(socket.AF_INET6, ip_address)
    except (OSError, socket.error):
        return False
    return True
