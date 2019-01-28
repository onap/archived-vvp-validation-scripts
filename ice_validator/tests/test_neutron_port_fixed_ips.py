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
#
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

"""
resources:
{vm-type}_{vm-type_index}_{network-role}_port_{port-index}:
  type: OS::Neutron::Port
  properties:
    network: { get_param: ...}
    fixed_ips: [ { "ipaddress": { get_param: ... } } ]
    binding:vnic_type: direct           #only SR-IOV ports, not OVS ports
    value_specs: {
      vlan_filter: { get_param: ... },  #all NC ports
      public_vlans: { get_param: ... }, #all NC ports
      private_vlans: { get_param: ... },#all NC ports
      guest_vlans: { get_param: ... },  #SR-IOV Trunk Port only
      vlan_mirror: { get_param: ... },  #SRIOV Trunk Port
                                        # Receiving Mirrored Traffic only
     ATT_FABRIC_CONFIGURATION_REQUIRED: true #all NC ports
    }
  metadata:
    port_type: SR-IOV_Trunk             #SR-IOV Trunk Port
    port_type: SR-IOV_Non_Trunk         #SR-IOV Non Trunk Port
    port_type: OVS                      #OVS Port
    port_type: SR-IOV_Mirrored_Trunk    #SR-IOV Trunk Port
                                        # Receiving Mirrored Traffic
"""

import os
import os.path
import re

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.3.0"

RE_BASE = re.compile(r"(^base$)|(^base_)|(_base_)|(_base$)")  # search pattern

RE_EXTERNAL_PARAM_SUBNET_ID = re.compile(  # match pattern
    r"(?P<network_role>.+)(_v6)?_subnet_id$"
)
RE_EXTERNAL_PARAM_SUBNET = RE_EXTERNAL_PARAM_SUBNET_ID
# RE_EXTERNAL_PARAM_SUBNET = re.compile( # match pattern
#        r'(?P<network_role>.+)(_v6)?_subnet$')

RE_INTERNAL_PARAM_SUBNET_ID = re.compile(  # match pattern
    r"int_(?P<network_role>.+)(_v6)?_subnet_id$"
)
RE_INTERNAL_PARAM_SUBNET = RE_INTERNAL_PARAM_SUBNET_ID
# RE_INTERNAL_PARAM_SUBNET = re.compile( # match pattern
#        r'int_(?P<network_role>.+)(_v6)?_subnet$')


def get_network(base_template_filepath):
    """Return the base template's Heat instance.
    """
    if base_template_filepath is None:
        pytest.skip("No base template found")
    base_template = Heat(filepath=base_template_filepath)
    for r in base_template.resources.values():
        if (
            base_template.nested_get(r, "type") == "OS::Neutron::Net"
            or base_template.nested_get(r, "type") == "OS::ContrailV2::VirtualNetwork"
        ):
            return base_template
    return None


def run_test(heat_template, validate):
    """call validate for each fixed_ips
    """
    heat = Heat(filepath=heat_template)
    base_template = get_base_template(heat_template)
    if not heat.resources:
        pytest.skip("No resources found")

    neutron_ports = heat.neutron_port_resources
    if not neutron_ports:
        pytest.skip("No OS::Neutron::Port resources found")

    bad = {}
    for rid, resource in neutron_ports.items():
        fixed_ips = heat.nested_get(resource, "properties", "fixed_ips")
        if fixed_ips is None:
            continue
        if not isinstance(fixed_ips, list):
            bad[rid] = "properties.fixed_ips must be a list."
            continue
        if not heat.parameters:
            bad[rid] = "fixed_ips requires parameters"
            continue
        for fixed_ip in fixed_ips:
            error = validate(heat, fixed_ip, base_template)
            if error:
                bad[rid] = error
                break
    if bad:
        # raise RuntimeError(
        raise AssertionError(
            "Bad OS::Neutron::Port: %s"
            % (", ".join("%s: %s" % (rid, error) for rid, error in bad.items()))
        )


def validate_external_fixed_ip(heat, fixed_ip, base_template):
    """ensure fixed_ip subnet and subnet_id for external network
    match the pattern.
    Returns error message string or None.
    """
    subnet = heat.nested_get(fixed_ip, "subnet", "get_param")
    subnet_id = heat.nested_get(fixed_ip, "subnet_id", "get_param")
    if subnet and subnet_id:
        error = 'fixed_ip %s has both "subnet" and "subnet_id"' % (fixed_ip)
    elif subnet:
        error = validate_external_subnet(subnet)
    elif subnet_id:
        error = validate_external_subnet_id(subnet_id)
    else:
        error = None
    return error


def validate_external_subnet(subnet):
    """ensure subnet matches template.
    Returns error message string or None.
    """
    if (
        subnet
        and not subnet.startswith("int_")
        and RE_EXTERNAL_PARAM_SUBNET.match(subnet) is None
    ):
        return 'fixed_ip subnet parameter "%s" does not match "%s"' % (
            subnet,
            RE_EXTERNAL_PARAM_SUBNET.pattern,
        )
    return None


def validate_external_subnet_id(subnet_id):
    """ensure subnet_id matches template.
    Returns error message string or None.
    """
    if (
        subnet_id
        and not subnet_id.startswith("int_")
        and RE_EXTERNAL_PARAM_SUBNET_ID.match(subnet_id) is None
    ):
        return 'fixed_ip subnet_id parameter "%s" does not match "%s"' % (
            subnet_id,
            RE_EXTERNAL_PARAM_SUBNET_ID.pattern,
        )
    return None


def validate_internal_fixed_ip(heat, fixed_ip, base_template):
    """ensure fixed_ip subnet and subnet_id for internal network
    match the pattern.
    Returns error message string or None.
    """
    base_module = get_network(base_template)
    subnet = heat.nested_get(fixed_ip, "subnet", "get_param")
    subnet_id = heat.nested_get(fixed_ip, "subnet_id", "get_param")
    if subnet and subnet_id:
        error = 'fixed_ip %s has both "subnet" and "subnet_id"' % (fixed_ip)
    elif subnet:
        error = validate_internal_subnet(heat, base_module, subnet)
    elif subnet_id:
        error = validate_internal_subnet_id(heat, base_module, subnet_id)
    else:
        error = None
    return error


def validate_internal_subnet(heat, base_module, subnet):
    """ensure if subnet matches template then its parameter exists.
    Returns error message string or None.
    """
    if (
        subnet
        and subnet.startswith("int_")
        and RE_INTERNAL_PARAM_SUBNET.match(subnet)
        and heat.nested_get(base_module.outputs, subnet) is None
    ):
        return 'fixed_ip subnet parameter "%s" not in base outputs"' % (subnet)
    return None


def validate_internal_subnet_id(heat, base_module, subnet_id):
    """ensure if subnet_id matches template then its parameter exists.
    Returns error message string or None.
    """
    if (
        subnet_id
        and subnet_id.startswith("int_")
        and RE_INTERNAL_PARAM_SUBNET_ID.match(subnet_id)
        and heat.nested_get(base_module.outputs, subnet_id) is None
    ):
        return 'fixed_ip subnet_id parameter "%s" not in base outputs"' % (subnet_id)
    return None


def validate_fixed_ip(heat, fixed_ip, base_template):
    """ensure fixed_ip has proper parameters
    Returns error message string or None.
    """
    subnet = heat.nested_get(fixed_ip, "subnet", "get_param")
    subnet_id = heat.nested_get(fixed_ip, "subnet_id", "get_param")
    if subnet and subnet_id:
        error = 'fixed_ip %s has both "subnet" and "subnet_id"' % (fixed_ip)
    elif subnet and heat.nested_get(heat.parameters, subnet, "type") != "string":
        error = 'subnet parameter "%s" must be type "string"' % subnet
    elif subnet_id and heat.nested_get(heat.parameters, subnet_id, "type") != "string":
        error = 'subnet_id parameter "%s" must be type "string"' % subnet_id
    else:
        error = None
    return error


def get_base_template(heat_template):
    (dirname, filename) = os.path.split(heat_template)
    files = os.listdir(dirname)
    for file in files:
        basename, __ = os.path.splitext(os.path.basename(file))
        if (
            __ == ".yaml"
            and basename.find("base") != -1
            and basename.find("volume") == -1
        ):
            return os.path.join(dirname, "{}{}".format(basename, __))
    return None


@validates("R-38236")
def test_neutron_port_fixed_ips(heat_template):
    """
    The VNF's Heat Orchestration Template's
    resource ``OS::Neutron::Port`` property ``fixed_ips``
    map property ``subnet``/``subnet_id`` parameter
    **MUST** be declared type ``string``.
    """
    run_test(heat_template, validate_fixed_ip)


@validates("R-62802", "R-15287")
def test_neutron_port_external_fixed_ips(heat_template):
    """
    When the VNF's Heat Orchestration Template's
    resource ``OS::Neutron::Port`` is attaching
    to an external network,
    and an IPv4 address is being cloud assigned by OpenStack's DHCP Service
    and the external network IPv4 subnet is to be specified
    using the property ``fixed_ips``
    map property ``subnet``/``subnet_id``, the parameter
    **MUST** follow the naming convention

      * ``{network-role}_subnet_id``
    and the external network IPv6 subnet is to be specified
      * ``{network-role}_v6_subnet_id``
    """
    run_test(heat_template, validate_external_fixed_ip)


@validates("R-84123", "R-76160")
def test_neutron_port_internal_fixed_ips(heat_template):
    """
    When

      * the VNF's Heat Orchestration Template's
        resource ``OS::Neutron::Port`` in an Incremental Module is attaching
        to an internal network
        that is created in the Base Module, AND
      * an IPv4 address is being cloud assigned by OpenStack's DHCP Service AND
      * the internal network IPv4 subnet is to be specified
        using the property ``fixed_ips`` map property ``subnet``/``subnet_id``,

    the parameter **MUST** follow the naming convention

      * ``int_{network-role}_subnet_id``
    an IPv6 address is being cloud assigned by OpenStack's DHCP Service AND
      * ``int_{network-role}_v6_subnet_id``

    """
    run_test(heat_template, validate_internal_fixed_ip)
