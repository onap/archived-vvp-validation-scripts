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

import os.path
import re

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"

RE_BASE = re.compile(r"(^base$)|(^base_)|(_base_)|(_base$)")  # search pattern
RE_NEUTRON_PORT_RID = re.compile(  # match pattern
    r"(?P<vm_type>.+)"
    r"_(?P<vm_type_index>\d+)"
    r"_(?P<network_role>.+)"
    r"_port_"
    r"(?P<port_index>\d+)"
    r"$"
)
RE_INTERNAL_NETWORK_PARAM = re.compile(  # match pattern
    r"int_(?P<network_role>.+)_net_(?P<value_type>id|name)$"
)
RE_INTERNAL_NETWORK_RID = re.compile(  # match pattern
    r"int_(?P<network_role>.+)_network$"
)


def get_base_template_filepath(yaml_files):
    """Return first filepath to match RE_BASE
    """
    for filepath in yaml_files:
        basename, __ = os.path.splitext(os.path.basename(filepath))
        if RE_BASE.search(basename) and basename.find("volume") == -1:
            return filepath
    return None


def get_internal_network(yaml_files):
    """Return the base template's Heat istance.
    """
    base_template_filepath = get_base_template_filepath(yaml_files)
    if base_template_filepath is None:
        pytest.skip("No base template found")
    base_template = Heat(filepath=base_template_filepath)
    for r in base_template.resources.values():
        # if base_template.nested_get(r, 'type') == 'OS::Neutron::Net':
        return base_template

    return None


def get_neutron_ports(heat):
    """Return dict of resource_id: resource, whose type is
    OS::Neutron::Port.
    """
    return {
        rid: resource
        for rid, resource in heat.resources.items()
        if heat.nested_get(resource, "type") == "OS::Neutron::Port"
    }


# pylint: disable=invalid-name


@validates("R-86182", "R-22688")
def test_neutron_port_internal_network(yaml_files):
    """
    When the VNF's Heat Orchestration Template's Resource
    ``OS::Neutron::Port`` is attaching to an internal network,
    and the internal network is created in a
    different Heat Orchestration Template than the ``OS::Neutron::Port``,
    the ``network`` parameter name **MUST**

      * follow the naming convention ``int_{network-role}_net_id``
        if the Neutron
        network UUID value is used to reference the network
      * follow the naming convention ``int_{network-role}_net_name`` if the
        OpenStack network name in is used to reference the network.

    where ``{network-role}`` is the network-role of the internal network and
    a ``get_param`` **MUST** be used as the intrinsic function.

    In Requirement R-86182, the internal network is created in the VNF's
    Base Module (Heat Orchestration Template) and the parameter name is
    declared in the Base Module's ``outputs`` section.
    When the parameter's value uses a "get_param" function, its name
    must end in "_name", and when it uses a "get_resource" function,
    its name must end in "_id".

    The output parameter name will be declared as a parameter in the
    ``parameters`` section of the incremental module.
    """
    internal_network = get_internal_network(yaml_files)
    if not internal_network:
        pytest.skip("internal_network template not found")

    if not internal_network.outputs:
        pytest.skip('internal_network template has no "outputs"')

    for filepath in yaml_files:
        if filepath != internal_network.filepath:
            validate_neutron_port(filepath, internal_network)


def validate_neutron_port(filepath, internal_network):
    """validate the neutron port
    """
    heat = Heat(filepath=filepath)
    if not heat.resources:
        return
    neutron_ports = get_neutron_ports(heat)
    if not neutron_ports:
        return
    bad = {}
    for rid, resource in neutron_ports.items():
        if not heat.parameters:
            bad[rid] = 'missing "parameters"'
            continue
        network = heat.nested_get(resource, "properties", "network", "get_param")
        if network is None:
            bad[rid] = 'missing "network.get_param"'
            continue
        if not network.startswith("int_"):
            continue  # not an internal network port
        error = validate_param(heat, network, internal_network)
        if error:
            bad[rid] = error
    if bad:
        raise RuntimeError(
            "Bad OS::Neutron::Port: %s"
            % (", ".join("%s: %s" % (rid, error) for rid, error in bad.items()))
        )


def validate_param(heat, network, internal_network):
    """Ensure network (the parameter name) is defined in the base
    template, and has the correct value function.  Ensure its
    network-role is found in the base template in some
    OS::Neutron::Net resource.
    Return error message string, or None if no no errors.
    """
    match = RE_INTERNAL_NETWORK_PARAM.match(network)
    if not match:
        return 'network.get_param "%s" does not match "%s"' % (
            network,
            RE_INTERNAL_NETWORK_PARAM.pattern,
        )
    if heat.nested_get(heat.parameters, network) is None:
        return "missing parameters.%s" % network
    output = heat.nested_get(internal_network.outputs, network)
    if not output:
        return 'network.get_param "%s"' " not found in base template outputs" % network
    param_dict = match.groupdict()
    expect = {"name": "get_param", "id": "get_resource"}[param_dict["value_type"]]
    value = heat.nested_get(output, "value")
    if heat.nested_get(value, expect) is None:
        return (
            'network.get_param "%s" implies its base template'
            ' output value function should be "%s" dict not "%s"'
            % (network, expect, value)
        )
    network_role = param_dict["network_role"]
    for rid, resource in internal_network.resources.items():
        if (
            heat.nested_get(resource, "type") == "OS::Neutron::Net"
            or heat.nested_get(resource, "type") == "OS::ContrailV2::VirtualNetwork"
        ):
            match = RE_INTERNAL_NETWORK_RID.match(rid)
            if match and match.groupdict()["network_role"] == network_role:
                return None
    return (
        "OS::Neutron::Net with network-role"
        ' "%s" not found in base template."' % network_role
    )
