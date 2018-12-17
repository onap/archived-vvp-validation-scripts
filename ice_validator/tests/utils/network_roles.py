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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

import re
import socket

PARAM_FORMATS = [
    ["network", "string", "internal", re.compile(r"int_(.+?)_net_id")],
    ["network", "string", "internal", re.compile(r"int_(.+?)_net_name")],
    ["network", "string", "external", re.compile(r"(.+?)_net_id")],
    ["network", "string", "external", re.compile(r"(.+?)_net_name")],
]

RESOURCE_FORMATS = [
    re.compile(r"int_(.+?)_network"),  # OS::ContrailV2::VirtualNetwork
    re.compile(r"int_(.+?)_RVN"),  # OS::ContrailV2::VirtualNetwork
    re.compile(r"int_(.+?)"),  # OS::Neutron::Net
]


def get_network_role_and_type(resource):
    """
    Derive the network role and type (internal vs. external) from an
    OS::Neutron::Port.

    :param resource: dict of Resource attributes
    :return: tuple of (network_role, network_type) where network_type is
             'internal' or 'external'.  Returns (None, None) if resource
             is not a port or the values cannot be derived.
    """
    if not isinstance(resource, dict):
        return None, None
    if resource.get("type", "") != "OS::Neutron::Port":
        return None, None

    network_props = resource.get("properties", {}).get("network", {})
    is_resource = "get_resource" in network_props
    if is_resource:
        network = network_props.get("get_resource", "")
    else:
        network = network_props.get("get_param", "")

    if is_resource:  # connecting to an network in the template
        for format in RESOURCE_FORMATS:
            m = format.match(network)
            if m and m.group(1):
                return m.group(1), "internal"
    else:
        for format in PARAM_FORMATS:
            m = format[3].match(network)
            if m and m.group(1):
                return m.group(1), format[2]
    return None, None


def get_network_role_from_port(resource):
    """
    Get the network-role from a OS::Neutron::Port resource.  Returns None
    if resource is not a port or the network-role cannot be derived
    """
    return get_network_role_and_type(resource)[0]


def get_network_roles(resources, of_type=""):
    """
    Returns the network roles derived from the OS::Neutron::Port resources
    in the collection of ``resources``.  If ``of_type`` is not specified
    then all network roles will be returned, or ``external`` or ``internal``
    can be passed to select only those network roles

    :param resources:   collection of resource attributes (dict)
    :param of_type:     "internal" or "external"
    :return:            set of network roles discovered
    """
    valid_of_type = ("", "external", "internal")
    if of_type not in ("", "external", "internal"):
        raise RuntimeError("of_type must one of " + ", ".join(valid_of_type))
    network_roles = set()
    for v in resources.values():
        nr, nt = get_network_role_and_type(v)
        if not nr:
            continue
        if not of_type:
            network_roles.add(nr)
        elif of_type and of_type == nt:
            network_roles.add(nr)
    return network_roles


def get_network_type_from_port(resource):
    """
    Get the network-type (internal or external) from an OS::Neutron::Port
    resource.  Returns None if the resource is not a port or the type
    cannot be derived.
    """
    return get_network_role_and_type(resource)[1]


def is_valid_ip_address(ip_address, ip_type="ipv4"):
    """
    check if an ip address is valid
    """
    if ip_type == "ipv4":
        return is_valid_ipv4_address(ip_address)
    elif ip_type == "ipv6":
        return is_valid_ipv6_address(ip_address)
    return False


def is_valid_ipv4_address(ip_address):
    """
    check if an ip address of the type ipv4
    is valid
    """
    try:
        socket.inet_pton(socket.AF_INET, ip_address)
    except AttributeError:
        try:
            socket.inet_aton(ip_address)
        except (OSError, socket.error):
            return False
        return ip_address.count(".") == 3
    except (OSError, socket.error):
        return False
    return True


def is_valid_ipv6_address(ip_address):
    """
    check if an ip address of the type ipv6
    is valid
    """
    try:
        socket.inet_pton(socket.AF_INET6, ip_address)
    except (OSError, socket.error):
        return False
    return True


def property_uses_get_resource(resource, property_name):
    """
    returns true if a port's network property
    uses the get_resource function
    """
    if not isinstance(resource, dict):
        return False
    if "properties" not in resource:
        return False
    for k1, v1 in resource["properties"].items():
        if k1 != property_name:
            continue
        if isinstance(v1, dict) and "get_resource" in v1:
            return True
    return False
