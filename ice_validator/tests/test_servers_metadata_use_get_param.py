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


def check_servers_metadata_use_get_param(yaml_file, md):
    """
    Check all defined nova server instances include
    metadata via the get_param function
    """

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    invalid_nova_servers = []

    for k1, v1 in yml["resources"].items():
        if "type" not in v1:
            continue
        if v1["type"] == "OS::Nova::Server":
            try:
                for k2, v2 in v1["properties"]["metadata"].items():
                    if k2 == md:
                        if isinstance(v2, dict):
                            metadata = v2.get("get_param")
                            if not metadata:
                                invalid_nova_servers.append(
                                    {"server": k1, "metadata": k2}
                                )
                        else:
                            invalid_nova_servers.append({"server": k1, "metadata": k2})
            except Exception as e:
                print(e)
                invalid_nova_servers.append(k1)

    assert (
        not invalid_nova_servers
    ), "OS::Nova::Server metadata MUST use get_param {}".format(invalid_nova_servers)


@validates("R-37437")
def test_servers_vnf_id_metadata_use_get_param(yaml_file):
    check_servers_metadata_use_get_param(yaml_file, "vnf_id")


@validates("R-71493")
def test_servers_vf_module_id_metadata_use_get_param(yaml_file):
    check_servers_metadata_use_get_param(yaml_file, "vf_module_id")


@validates("R-72483")
def test_servers_vnf_name_metadata_use_get_param(yaml_file):
    check_servers_metadata_use_get_param(yaml_file, "vnf_name")


@validates("R-68023")
def test_servers_vf_module_name_metadata_use_get_param(yaml_file):
    check_servers_metadata_use_get_param(yaml_file, "vf_module_name")


@validates("R-50816")
def test_servers_vf_module_index_metadata_use_get_param(yaml_file):
    check_servers_metadata_use_get_param(yaml_file, "vf_module_index")
