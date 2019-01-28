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

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"


def is_v6_ip(ip_address):
    if ip_address.find("v6") != -1:
        return True
    return False


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


def run_test(heat_template, validate):
    """call validate with allowed_address_pairs
    """
    heat = Heat(filepath=heat_template)
    if not heat.resources:
        pytest.skip("No resources found")

    neutron_ports = get_neutron_ports(heat)
    if not neutron_ports:
        pytest.skip("No OS::Neutron::Port resources found")

    bad = {}
    for rid, resource in neutron_ports.items():
        if rid.startswith("int_"):
            continue
        allowed_address_pairs = heat.nested_get(
            resource, "properties", "allowed_address_pairs"
        )
        if allowed_address_pairs is None:
            continue
        if not isinstance(allowed_address_pairs, list):
            bad[rid] = "properties.allowed_address_pairs must be a list."
            continue
        error = validate(heat, allowed_address_pairs)
        if error:
            bad[rid] = error
            break
    if bad:
        # raise RuntimeError(
        raise AssertionError(
            "Bad OS::Neutron::Port: %s"
            % (", ".join("%s: %s" % (rid, error) for rid, error in bad.items()))
        )


def validate_field(heat, allowed_address_pairs, field, v6=False):
    """ensure at most one `field` is found in `allowed_address_pairs'
    validate allowed_addrfess_pairs as well.
    Returns error message string or None.
    """
    error = None
    ports = set()
    port_type = "ipv6" if v6 else "ipv4"
    for allowed_address_pair in allowed_address_pairs:
        if not isinstance(allowed_address_pair, dict):
            error = 'allowed_address_pair "%s" is not a dict' % (allowed_address_pair)
            break
        if field in allowed_address_pair:
            param = heat.nested_get(allowed_address_pair, field, "get_param")
            if param is None:
                error = 'allowed_address_pair %s requires "get_param"' % field
                break
            else:
                # if v6 and testing v6, or inverse
                param = param[0] if isinstance(param, list) else param
                if v6 == is_v6_ip(param):
                    ports.add(param)
    if error is None and len(ports) > 1:
        error = 'More than one %s "%s" found in allowed_address_pairs: %s' % (
            port_type,
            field,
            list(ports),
        )
    return error


def validate_external_ipaddress(heat, allowed_address_pairs):
    """ensure allowed_address_pairs has at most one ip_address
    Returns error message string or None.
    """
    return validate_field(heat, allowed_address_pairs, "ip_address")


def validate_external_ipaddress_v6(heat, allowed_address_pairs):
    """ensure allowed_address_pairs has at most one v6_ip_address
    Returns error message string or None.
    """
    return validate_field(heat, allowed_address_pairs, "ip_address", v6=True)


# pylint: disable=invalid-name


@validates("R-91810")
def test_neutron_port_external_ipaddress(heat_template):
    """
    If a VNF requires ONAP to assign a Virtual IP (VIP) Address to
    ports connected an external network, the port
    **MUST NOT** have more than one IPv4 VIP address.
    """
    run_test(heat_template, validate_external_ipaddress)


@validates("R-41956")
def test_neutron_port_external_ipaddress_v6(heat_template):
    """
    If a VNF requires ONAP to assign a Virtual IP (VIP) Address to
    ports connected an external network, the port
    **MUST NOT** have more than one IPv6 VIP address.
    """
    run_test(heat_template, validate_external_ipaddress_v6)


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
