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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#
"""
resources:
{vm-type}_server_{vm-type_index}
"""
import pytest

from .structures import Heat
from .structures import ContrailV2InstanceIpProcessor
from .helpers import validates

VERSION = "2.0.0"


def run_test(heat_template, regex_names, network_flavor):
    """run test
    """
    heat = Heat(filepath=heat_template)
    processor = ContrailV2InstanceIpProcessor
    resource_type = processor.resource_type
    resources = heat.get_resource_by_type(resource_type=resource_type)
    if not resources:
        pytest.skip("No %s resources found" % resource_type)
    bad = []
    rid_patterns = processor.get_rid_patterns()
    for rid, resource in resources.items():
        flavor = processor.get_network_flavor(resource)
        if flavor != network_flavor:
            continue
        regex_name = processor.get_rid_match_tuple(rid)[0]
        if regex_name in regex_names:
            continue
        bad.append(rid)
    assert not bad, "%s resource ids %s must match one of %s" % (
        network_flavor,
        bad,
        [v for k, v in rid_patterns.items() if k in regex_names],
    )


# pylint: disable=invalid-name


@validates("R-53310", "R-46128")
def test_contrail_instance_ip_resource_id_external(heat_template):
    """
    A VNF's Heat Orchestration Template's Resource OS::ContrailV2::InstanceIp
    that is configuring an IPv4 Address on a port attached to an external
    network
    Resource ID **MUST** use the naming convention

    {vm-type}_{vm-type_index}_{network-role}_vmi_{vmi_index}
            _IP_{index}

    A VNF's Heat Orchestration Template's Resource OS::ContrailV2::InstanceIp
    that is configuring an IPv6 Address on a port attached to an external
    network
    Resource ID **MUST** use the naming convention

    {vm-type}_{vm-type_index}_{network-role}_vmi_{vmi_index}
            _v6_IP_{index}

    """

    run_test(
        heat_template,
        regex_names=("ip", "v6_ip"),
        network_flavor=ContrailV2InstanceIpProcessor.network_flavor_external,
    )


@validates("R-62187", "R-87563")
def test_contrail_instance_ip_resource_id_internal(heat_template):
    """
    internal
    {vm-type}_{vm-type_index}_int_{network-role}_vmi_{vmi_index}
            _IP_{index}
    {vm-type}_{vm-type_index}_int_{network-role}_vmi_{vmi_index}
            _v6_IP_{index}
    """
    run_test(
        heat_template,
        regex_names=("int_ip", "int_v6_ip"),
        network_flavor=ContrailV2InstanceIpProcessor.network_flavor_internal,
    )


@validates("R-20947", "R-88540")
def test_contrail_instance_ip_resource_id_subint(heat_template):
    """
    subint
    {vm-type}_{vm-type_index}_subint_{network-role}_vmi_{vmi_index}
            _IP_{index}
    {vm-type}_{vm-type_index}_subint_{network-role}_vmi_{vmi_index}
            _v6_IP_{index}
    """
    run_test(
        heat_template,
        regex_names=("subint_ip", "subint_v6_ip"),
        network_flavor=ContrailV2InstanceIpProcessor.network_flavor_subint,
    )
