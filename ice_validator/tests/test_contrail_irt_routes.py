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
contrail interface route table routes

resources:
<resource name>:
  type: OS::ContrailV2::InterfaceRouteTable
  depends_on: [resource name of OS::ContrailV2::ServiceInstance]
  properties:
    name:
      str_replace:
        template: VNF_NAME_interface_route_table
        params:
          VNF_NAME: { get_param: vnf_name }
    interface_route_table_routes:
      interface_route_table_routes_route: { get_param: fw_oam_route_prefixes }
    service_instance_refs:
      - get_resource: <resource name of OS::ContrailV2::ServiceInstance>
    service_instance_refs_data:
      - service_instance_refs_data_interface_type:
        { get_param: oam_interface_type }
"""

import re

import pytest

from .structures import Heat
from .helpers import validates

VERSION = "1.1.0"

RE_ROUTE_ROUTE_PARAM = re.compile(
    r"(?P<vm_type>.+)" r"_(?P<network_role>.+)" r"_route_prefixes" r"$"
)


def run_test(heat_template, validate):
    """call validate for each routes route
    """
    heat = Heat(filepath=heat_template)
    if not heat.resources:
        pytest.skip("No resources found")

    irts = heat.get_resource_by_type(
        resource_type="OS::ContrailV2::InterfaceRouteTable"
    )
    if not irts:
        pytest.skip("No Contrail InterfaceRouteTable found")

    skip = True
    bad = {}
    for rid, resource in irts.items():
        routes_route = heat.nested_get(
            resource,
            "properties",
            "interface_route_table_routes",
            "interface_route_table_routes_route",
        )
        if routes_route is None:
            continue
        error = validate(heat, routes_route)
        if error:
            bad[rid] = error
            continue
        skip = False
    if bad:
        raise AssertionError(
            "Bad OS::ContrailV2::InterfaceRouteTable: %s"
            % (", ".join("%s: %s" % (rid, error) for rid, error in bad.items()))
        )
    if skip:
        pytest.skip("No Contrail routes_route found")


def validate_irt_route_param_format(heat, routes_route):
    """ensure routes_route has proper format.
    Returns error message string or None.
    """
    param = heat.nested_get(routes_route, "get_param")
    if param is None:
        return "missing routes_route get_param"
    match = RE_ROUTE_ROUTE_PARAM.match(param)
    if match is None:
        return 'routes_route get_param "%s" must match "%s"' % (
            param,
            RE_ROUTE_ROUTE_PARAM.pattern,
        )
    return None


def validate_irt_route_param_type(heat, routes_route):
    """ensure routes_route has proper type.
    Returns error message string or None.
    """
    param = heat.nested_get(routes_route, "get_param")
    if param is None:
        return None
    if heat.nested_get(heat.parameters, param, "type") != "json":
        return (
            'routes_route get_param "%s" '
            'must have a parameter of type "json"' % param
        )
    return None


# pylint: disable=invalid-name


@validates("R-28222")
def test_contrail_irt_route_param_format(heat_template):
    """
    If a VNF's Heat Orchestration Template
    ``OS::ContrailV2::InterfaceRouteTable`` resource
    ``interface_route_table_routes`` property
    ``interface_route_table_routes_route`` map property parameter name
    **MUST** follow the format
    """
    run_test(heat_template, validate_irt_route_param_format)


@validates("R-19756")
def test_contrail_irt_route_param_type(heat_template):
    """
    * ``{vm-type}_{network-role}_route_prefixes``
    **MUST** be defined as type ``json``.
    """
    run_test(heat_template, validate_irt_route_param_type)
