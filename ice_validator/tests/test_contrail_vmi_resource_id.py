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
resources:
{vm-type}_server_{vm-type_index}
"""
import pytest

from .structures import Heat
from .structures import ContrailV2VirtualMachineInterfaceProcessor
from .helpers import validates

VERSION = "2.0.0"


def run_test(heat_template, regex_name, network_flavor):
    """run test
    """
    heat = Heat(filepath=heat_template)
    heat_object_class = ContrailV2VirtualMachineInterfaceProcessor
    resource_type = heat_object_class.resource_type
    resources = heat.get_resource_by_type(resource_type=resource_type)
    if not resources:
        pytest.skip("No %s resources found" % resource_type)
    bad = []
    heat_object = heat_object_class()
    rid_pattern = heat_object.get_rid_patterns()[regex_name]
    for rid, resource in resources.items():
        flavor = heat_object.get_network_flavor(resource)
        if flavor != network_flavor:
            continue
        name = heat_object.get_rid_match_tuple(rid)[0]
        if name == regex_name:
            continue
        bad.append(rid)
    assert not bad, "%s resource ids %s must match %s" % (
        network_flavor,
        bad,
        [rid_pattern],
    )


# pylint: disable=invalid-name


@validates("R-96253")
def test_contrail_instance_ip_resource_id_external(yaml_file):
    """
    A VNF's Heat Orchestration Template's Resource
    OS::ContrailV2::VirtualMachineInterface that is attaching to an
    external network
    Resource ID **MUST** use the naming convention

    {vm-type}_{vm-type_index}_{network-role}_vmi_{vmi_index}
    """
    run_test(
        yaml_file,
        regex_name="external",
        network_flavor=ContrailV2VirtualMachineInterfaceProcessor.network_flavor_external,
    )


@validates("R-50468")
def test_contrail_instance_ip_resource_id_internal(yaml_file):
    """
    A VNF's Heat Orchestration Template's Resource
    OS::ContrailV2::VirtualMachineInterface that is attaching to an
    internal network
    Resource ID **MUST** use the naming convention

    {vm-type}_{vm-type_index}_int_{network-role}_vmi_{vmi_index}
    """
    run_test(
        yaml_file,
        regex_name="internal",
        network_flavor=ContrailV2VirtualMachineInterfaceProcessor.network_flavor_internal,
    )
