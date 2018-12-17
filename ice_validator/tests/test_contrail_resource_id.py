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
contrail
"""

import pytest
from .structures import ContrailV2InterfaceRouteTable
from .structures import ContrailV2NetworkIpam
from .structures import ContrailV2PortTuple
from .structures import ContrailV2ServiceHealthCheck
from .structures import ContrailV2ServiceTemplate
from .utils.network_roles import get_network_roles
from .utils.vm_types import get_vm_types
from .structures import Heat
from .helpers import validates

VERSION = "1.0.1"


def run_test(heat_template, contrail_class, get_parts, part_name):
    """
    run test
    """
    heat = Heat(filepath=heat_template)
    if not heat.resources:
        pytest.skip("No resources found")
    parts = get_parts(heat.resources)
    if not parts:
        pytest.skip("No %s found" % part_name)

    contrail_resources = heat.get_resource_by_type(
        resource_type=contrail_class.resource_type
    )
    if not contrail_resources:
        pytest.skip("No %s resources found" % contrail_class.resource_type)

    bad = []
    for rid in contrail_resources:
        if not any(heat.part_is_in_name(part, rid) for part in parts):
            bad.append(rid)
    if bad:
        raise AssertionError(
            "%s: %s"
            " must have %s in %s"
            % (contrail_class.resource_type, bad, part_name, list(parts))
        )


# pylint: disable=invalid-name


@validates("R-81214")
def test_contrail_interfaceroutetable_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    ``OS::ContrailV2::InterfaceRouteTable``
    Resource ID
    **MUST**
    contain the ``{network-role}``.
    """
    run_test(
        heat_template, ContrailV2InterfaceRouteTable, get_network_roles, "network_role"
    )


@validates("R-30753")
def test_contrail_networkipam_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    ``OS::ContrailV2::NetworkIpam``
    Resource ID
    **MUST**
    contain the ``{network-role}``.
    """
    run_test(heat_template, ContrailV2NetworkIpam, get_network_roles, "network_role")


@validates("R-20065")
def test_contrail_porttuple_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    ``OS::ContrailV2::PortTuple``
    Resource ID
    **MUST**
    contain the ``{vm-type}``.
    """
    run_test(heat_template, ContrailV2PortTuple, get_vm_types, "vm_type")


@validates("R-76014")
def test_contrail_servicehealthcheck_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    ``OS::ContrailV2::ServiceHealthCheck``
    Resource ID
    **MUST**
    contain the ``{vm-type}``.
    """
    run_test(heat_template, ContrailV2ServiceHealthCheck, get_vm_types, "vm_type")


@validates("R-16437")
def test_contrail_servicetemplate_resource_id(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource
    ``OS::ContrailV2::ServiceTemplate``
    Resource ID
    **MUST**
    contain the ``{vm-type}``.
    """
    run_test(heat_template, ContrailV2ServiceTemplate, get_vm_types, "vm_type")
