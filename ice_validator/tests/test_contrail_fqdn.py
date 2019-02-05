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
#

"""
contrail fqdn
"""

import re

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"

RE_NETWORK_ROLE = re.compile(
    r".+_" r"\d+_" r"(int_)?" r"(subint_)?" r"(?P<network_role>.+)" r"_vmi_" r"\d$"
)


def get_network_role(rid):
    """return the network_role parsed from the rid.
    """
    match = RE_NETWORK_ROLE.match(rid)
    return match.groupdict()["network_role"] if match else None


def run_test(heat_template, validate):
    """call validate for each fixed_ips
    """
    heat = Heat(filepath=heat_template)
    if not heat.resources:
        pytest.skip("No resources found")

    contrail_resources = heat.contrail_resources
    if not contrail_resources:
        pytest.skip("No Contrail resources found")

    skip = True
    bad = {}
    for rid, resource in contrail_resources.items():
        network_role = get_network_role(rid)
        if network_role is None:
            continue
        virtual_network_refs = heat.nested_get(
            resource, "properties", "virtual_network_refs"
        )
        if virtual_network_refs is None:
            continue
        if not isinstance(virtual_network_refs, list):
            bad[rid] = "properties.virtual_network_refs must be a list."
            continue
        error = validate(heat, virtual_network_refs, network_role)
        if error:
            bad[rid] = error
            continue
        skip = False
    if bad:
        raise AssertionError(
            "Bad OS::ContrailV2::VirtualMachineInterface: %s"
            % (", ".join("%s: %s" % (rid, error) for rid, error in bad.items()))
        )
    if skip:
        pytest.skip("No Contrail virtual_network_refs found")


def validate_virtual_network_refs(heat, virtual_network_refs, network_role):
    """ensure there is a matching virtual_network_ref in the list.
    Returns error message string or None.
    """
    expect = "%s_net_fqdn" % network_role
    for vn_ref in virtual_network_refs:
        param = heat.nested_get(vn_ref, "get_param")
        if param == expect:
            param_type = heat.nested_get(heat.parameters, param, "type")
            if param_type != "string":
                return (
                    'virtual_network_ref parameter "%s" '
                    'type "%s" must be "string"' % (param, param_type)
                )
            else:
                return None
    return "virtual_network_refs must include {get_param: %s}" % expect


# pylint: disable=invalid-name


@validates("R-02164")
def test_contrail_fqdn(yaml_file):
    """
    When a VNF's Heat Orchestration Template's Contrail resource
    has a property that
    references an external network that requires the network's
    Fully Qualified Domain Name (FQDN), the property parameter

    * **MUST** follow the format ``{network-role}_net_fqdn``
    * **MUST** be declared as type ``string``
    """
    run_test(yaml_file, validate_virtual_network_refs)
