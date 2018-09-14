# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.vm_types import get_vm_type_for_nova_server


@validates('R-40499',
           'R-57282')
def test_nova_servers_valid_resource_ids(yaml_file):
    '''
    Make sure all nova servers have valid resource ids
    '''

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_nova_servers = []
    for k1, v1 in yml["resources"].items():
        if not isinstance(v1, dict):
            continue
        if "properties" not in v1:
            continue
        if v1.get("type") != "OS::Nova::Server":
            continue

        vm_type = get_vm_type_for_nova_server(v1)
        if not vm_type:
            # could not determine vm_type
            invalid_nova_servers.append({"resource": k1, "vm_type": "none found"})
        else:
            k1_split = k1.split("_server_")
            k1_prefix = k1_split[0]
            if k1_prefix != vm_type:
                # vm_type on server doesn't match
                invalid_nova_servers.append({"resource": k1, "vm_type": vm_type})
            else:
                if len(k1_split) == 2:
                    k1_suffix = k1_split[1]
                    try:
                        int(k1_suffix)
                    except ValueError:
                        # vm_type_index is not an integer
                        invalid_nova_servers.append({"resource": k1, "vm_type": vm_type, "vm_type_index": k1_suffix})
                else:
                    # vm_type_index not found
                    invalid_nova_servers.append({"resource": k1, "vm_type": vm_type, "vm_type_index": "none found"})

    assert not invalid_nova_servers, \
        "Invalid OS::Nova::Server resource ids detected {}\n" \
        "OS::Nova::Server resource ids must be in the form " \
        "<vm_type>_server_<vm_type_index> \n" \
        "<vm_type> is derived from flavor, image and name properties " \
        "".format(invalid_nova_servers)
