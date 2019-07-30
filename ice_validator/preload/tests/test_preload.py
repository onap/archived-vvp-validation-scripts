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

import os
import yaml

from preload.preload import Preload
from tests.utils import nested_dict


TEMPLATE_FILE = "{}/data/base_template.yaml".format(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_ENV = "{}/data/base_template.yaml".format(os.path.dirname(os.path.abspath(__file__)))


def load_dummy_data():
    with open(TEMPLATE_FILE, "r") as f:
        yml = yaml.safe_load(f)

    with open(TEMPLATE_ENV, "r") as f:
        env = yaml.safe_load(f)

    return yml, env


def test_vnf_name():

    vnf_name = "testvnf"

    preload = Preload(vnf_name, "test vnf type", TEMPLATE_FILE, "/tmp/outputs", preload_format="grapi")

    preload_vnf_name = nested_dict.get(
        preload.preload,
        "input",
        "preload-vf-module-topology-information",
        "vnf-topology-identifier-structure",
        "vnf-name",
        default=""
    )

    assert preload_vnf_name == vnf_name


def test_vnf_type():

    vnf_type = "testvnftype"

    preload = Preload("vnf_name", vnf_type, TEMPLATE_FILE, "/tmp/outputs", preload_format="grapi")

    preload_vnf_type = nested_dict.get(
        preload.preload,
        "input",
        "preload-vf-module-topology-information",
        "vnf-topology-identifier-structure",
        "vnf-type",
        default=""
    )

    assert preload_vnf_type == vnf_type


def test_network_name():

    network_name = "oam_net_id"
    network_present = False

    preload = Preload("vnf_name", "vnf_type", TEMPLATE_FILE, "/tmp/outputs", preload_format="grapi")
    networks = nested_dict.get(
        preload.preload,
        "input",
        "preload-vf-module-topology-information",
        "vnf-resource-assignments",
        "vnf-networks",
        "vnf-network",
        default=[]
    )

    for network in networks:
        pname = network.get("network-name", "")
        if pname == network_name:
            network_present = True
            break

    assert network_present

