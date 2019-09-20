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
import tempfile
from pathlib import Path
from shutil import rmtree

import pytest

from app_tests.preload_tests.test_grapi import load_json
from preload.environment import PreloadEnvironment
from preload.model import Vnf, get_heat_templates
from preload_vnfapi import VnfApiPreloadGenerator
from tests.helpers import load_yaml, first

THIS_DIR = Path(__file__).parent
SAMPLE_HEAT_DIR = THIS_DIR / "sample_heat"


def load_module(base_dir, name):
    path = Path(str(base_dir / "vnfapi" / name))
    assert path.exists(), "{} does not exist".format(path)
    return load_yaml(str(path))


@pytest.fixture(scope="session")
def session_dir(request):
    # Temporary directory that gets deleted at the session
    # pytest tmpdir doesn't support a non-function scoped temporary directory
    session_dir = Path(tempfile.mkdtemp())
    request.addfinalizer(lambda: rmtree(session_dir))
    return session_dir


@pytest.fixture(scope="session")
def preload(pytestconfig, session_dir):
    # Generate the preloads for testing
    def fake_getoption(opt, default=None):
        return [SAMPLE_HEAT_DIR.as_posix()] if opt == "template_dir" else None

    pytestconfig.getoption = fake_getoption
    templates = get_heat_templates(pytestconfig)
    vnf = Vnf(templates)
    preload_env = PreloadEnvironment(THIS_DIR / "sample_env")
    generator = VnfApiPreloadGenerator(vnf, session_dir, preload_env)
    generator.generate()
    return session_dir


@pytest.fixture(scope="session")
def base(preload):
    return load_module(preload, "base_incomplete.json")


@pytest.fixture(scope="session")
def incremental(preload):
    return load_module(preload, "incremental_incomplete.json")


def test_base_azs(base):
    az = base["input"]["vnf-topology-information"]["vnf-assignments"][
        "availability-zones"
    ]
    assert az == [
        {"availability-zone": "VALUE FOR: availability_zone_0"},
        {"availability-zone": "VALUE FOR: availability_zone_1"},
    ]


def test_base_networks(base):
    nets = base["input"]["vnf-topology-information"]["vnf-assignments"]["vnf-networks"]
    assert nets == [
        {
            "network-role": "oam",
            "network-name": "VALUE FOR: network name for oam_net_id",
            "subnet-id": "oam_subnet_id",
        },
        {"network-role": "ha", "network-name": "VALUE FOR: network name for ha_net_id"},
        {
            "network-role": "ctrl",
            "network-name": "VALUE FOR: network name for ctrl_net_id",
            "subnet-id": "ctrl_subnet_id",
        },
    ]


def test_base_vm_types(base):
    vms = base["input"]["vnf-topology-information"]["vnf-assignments"]["vnf-vms"]
    vm_types = {vm["vm-type"] for vm in vms}
    assert vm_types == {"db", "svc", "mgmt", "lb"}
    db = first(vms, lambda v: v["vm-type"] == "db")
    assert db == {
        "vm-type": "db",
        "vm-count": 2,
        "vm-names": {"vm-name": ["VALUE FOR: db_name_0", "VALUE FOR: db_name_1"]},
        "vm-networks": [
            {
                "network-role": "oam",
                "network-role-tag": "oam",
                "ip-count": 2,
                "ip-count-ipv6": 0,
                "floating-ip": "",
                "floating-ip-v6": "",
                "network-ips": [
                    {"ip-address": "VALUE FOR: db_oam_ip_0"},
                    {"ip-address": "VALUE FOR: db_oam_ip_1"},
                ],
                "network-ips-v6": [],
                "network-macs": [],
                "interface-route-prefixes": [],
                "use-dhcp": "N",
            },
            {
                "network-role": "ha",
                "network-role-tag": "ha",
                "ip-count": 0,
                "ip-count-ipv6": 0,
                "floating-ip": "VALUE FOR: db_ha_floating_ip",
                "floating-ip-v6": "VALUE FOR: db_ha_floating_v6_ip",
                "network-ips": [],
                "network-ips-v6": [],
                "network-macs": [],
                "interface-route-prefixes": [],
                "use-dhcp": "N",
            },
        ],
    }


def test_base_parameters(base):
    params = base["input"]["vnf-topology-information"]["vnf-parameters"]
    assert params == [
        {
            "vnf-parameter-name": "db_vol0_id",
            "vnf-parameter-value": "VALUE FOR: db_vol0_id",
        },
        {
            "vnf-parameter-name": "db_vol1_id",
            "vnf-parameter-value": "VALUE FOR: db_vol1_id",
        },
    ]


def test_incremental(incremental):
    az = incremental["input"]["vnf-topology-information"]["vnf-assignments"][
        "availability-zones"
    ]
    assert isinstance(az, list)
    assert len(az) == 1
    assert az[0] == {"availability-zone": "VALUE FOR: availability_zone_0"}


def test_incremental_networks(incremental):
    nets = incremental["input"]["vnf-topology-information"]["vnf-assignments"][
        "vnf-networks"
    ]
    assert isinstance(nets, list)
    assert len(nets) == 1
    assert nets[0]["network-role"] == "ha"


def test_preload_env_population(preload):
    base_path = THIS_DIR / "sample_env/preloads/vnfapi/base_incomplete.json"
    data = load_json(base_path)
    azs = data["input"]["vnf-topology-information"]["vnf-assignments"][
        "availability-zones"
    ]
    assert azs == [{"availability-zone": "az0"}, {"availability-zone": "az1"}]
