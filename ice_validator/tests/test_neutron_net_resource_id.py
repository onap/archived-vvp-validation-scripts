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
neutron net resource id
"""

import pytest

from .helpers import validates
from .structures import Heat
from .structures import NeutronNetProcessor

VERSION = "2.0.0"

# pylint: disable=invalid-name


@validates("R-25720")
def test_neutron_net_resource_id(yaml_file):
    """
    A VNF's Heat Orchestration Template's Resource OS::Neutron::Net
    Resource ID **MUST** use the naming convention

    * int_{network-role}_network
    """
    heat = Heat(filepath=yaml_file)
    neutron_nets = heat.get_resource_by_type(NeutronNetProcessor.resource_type)
    if not neutron_nets:
        pytest.skip("No neutron nets found")
    bad = []
    for rid in neutron_nets:
        if not NeutronNetProcessor.get_rid_match_tuple(rid)[0]:
            bad.append("Neutron Net %s does not match any known format" % rid)
    assert not bad, "; ".join(bad)
