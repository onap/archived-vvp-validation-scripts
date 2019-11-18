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

import collections
import re

from .structures import Heat
from .helpers import validates

VERSION = "1.2.0"


def case_mismatch(vm_type, param):
    """Return True if vm_type matches a portion of param in a case
    insensitive search, but does not equal that portion;
    return False otherwise.
    The "portions" of param are delimited by "_".
    """
    re_portion = re.compile(
        "(^(%(x)s)_)|(_(%(x)s)_)|(_(%(x)s)$)" % dict(x=vm_type), re.IGNORECASE
    )
    found = re_portion.search(param)
    if found:
        param_vm_type = [x for x in found.groups()[1::2] if x][0]
        return param_vm_type != vm_type
    else:
        return False


# pylint: disable=invalid-name


@validates("R-32394")
def test_vm_type_case(yaml_file):
    """
    A VNF's Heat Orchestration Template's use of ``{vm-type}`` in all Resource
    property parameter names **MUST** be the same case.
    """
    heat = Heat(filepath=yaml_file)
    resources = heat.resources
    bad = collections.defaultdict(list)
    for rid, resource in resources.items():
        vm_type = heat.get_vm_type(rid, resource=resource)
        if vm_type:
            properties = resource.get("properties")
            if isinstance(properties, dict):
                for prop, dic in properties.items():
                    param = heat.nested_get(dic, "get_param")
                    if isinstance(param, list):
                        param = param[0]
                    if isinstance(param, str) and case_mismatch(vm_type, param):
                        bad[(rid, vm_type)].append((prop, param))

    msg = 'vm-type/parameter case mis-match %s' \
        % '; '.join('resource: %s vm-type: %s %s' % (k[0], k[1],
                    ', '.join('%s: %s' % i for i in v)) for (k, v) in
                    bad.items())

    assert not bad, msg
