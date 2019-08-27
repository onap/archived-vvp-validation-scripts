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
import json
import tempfile
from pathlib import Path
from shutil import rmtree

import pytest

from preload.environment import PreloadEnvironment
from preload.model import Vnf, get_heat_templates
from preload_grapi import GrApiPreloadGenerator
from tests.helpers import first

THIS_DIR = Path(__file__).parent
SAMPLE_HEAT_DIR = THIS_DIR / "sample_heat"


def load_json(path):
    with path.open("r") as f:
        return json.load(f)


def load_module(base_dir, name):
    path = Path(str(base_dir / "grapi" / name))
    assert path.exists(), "{} does not exist".format(path)
    return load_json(path)


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
    env = PreloadEnvironment(THIS_DIR / "sample_env")
    vnf = Vnf(templates)
    generator = GrApiPreloadGenerator(vnf, session_dir, env)
    generator.generate()
    return session_dir


@pytest.fixture(scope="session")
def base(preload):
    return load_module(preload, "base.json")


@pytest.fixture(scope="session")
def incremental(preload):
    return load_module(preload, "incremental.json")


def test_base_fields(base):
    data = base["input"]["preload-vf-module-topology-information"][
        "vnf-topology-identifier-structure"
    ]
    assert data["vnf-name"] == "VALUE FOR: vnf_name"
    assert "<Service Name>/<VF Instance Name>" in data["vnf-type"]


def test_base_azs(base):
    az = base["input"]["preload-vf-module-topology-information"][
        "vnf-resource-assignments"
    ]["availability-zones"]["availability-zone"]
    assert isinstance(az, list)
    assert len(az) == 2
    assert az[0] == "VALUE FOR: availability_zone_0"


def test_base_networks(base):
    nets = base["input"]["preload-vf-module-topology-information"][
        "vnf-resource-assignments"
    ]["vnf-networks"]["vnf-network"]
    assert isinstance(nets, list)
    assert len(nets) == 3
    oam = first(nets, lambda n: n["network-role"] == "oam")
    assert oam == {
        "network-role": "oam",
        "network-name": "VALUE FOR: network name of oam_net_id",
        "subnets-data": {"subnet-data": [{"subnet-id": "VALUE FOR: oam_subnet_id"}]},
    }


def test_base_vm_types(base):
    vms = base["input"]["preload-vf-module-topology-information"]["vf-module-topology"][
        "vf-module-assignments"
    ]["vms"]["vm"]
    vm_types = {vm["vm-type"] for vm in vms}
    assert vm_types == {"db", "svc", "mgmt", "lb"}
    db = first(vms, lambda v: v["vm-type"] == "db")
    assert db == {
        "vm-type": "db",
        "vm-count": 2,
        "vm-names": {"vm-name": ["VALUE FOR: db_name_0", "VALUE FOR: db_name_1"]},
        "vm-networks": {
            "vm-network": [
                {
                    "network-role": "oam",
                    "network-information-items": {
                        "network-information-item": [
                            {
                                "ip-version": "4",
                                "use-dhcp": "N",
                                "ip-count": 2,
                                "network-ips": {
                                    "network-ip": [
                                        "VALUE FOR: db_oam_ip_0",
                                        "VALUE FOR: db_oam_ip_1",
                                    ]
                                },
                            },
                            {
                                "ip-version": "6",
                                "use-dhcp": "N",
                                "ip-count": 0,
                                "network-ips": {"network-ip": []},
                            },
                        ]
                    },
                    "mac-addresses": {"mac-address": []},
                    "floating-ips": {"floating-ip-v4": [], "floating-ip-v6": []},
                    "interface-route-prefixes": {"interface-route-prefix": []},
                },
                {
                    "network-role": "ha",
                    "network-information-items": {
                        "network-information-item": [
                            {
                                "ip-version": "4",
                                "use-dhcp": "N",
                                "ip-count": 0,
                                "network-ips": {"network-ip": []},
                            },
                            {
                                "ip-version": "6",
                                "use-dhcp": "N",
                                "ip-count": 0,
                                "network-ips": {"network-ip": []},
                            },
                        ]
                    },
                    "mac-addresses": {"mac-address": []},
                    "floating-ips": {
                        "floating-ip-v4": ["VALUE FOR: db_ha_floating_ip"],
                        "floating-ip-v6": ["VALUE FOR: db_ha_floating_v6_ip"],
                    },
                    "interface-route-prefixes": {"interface-route-prefix": []},
                },
            ]
        },
    }


def test_base_general(base):
    general = base["input"]["preload-vf-module-topology-information"][
        "vf-module-topology"
    ]["vf-module-topology-identifier"]
    assert (
        general["vf-module-type"] == "VALUE FOR: <vfModuleModelName> from CSAR or SDC"
    )
    assert general["vf-module-name"] == "VALUE FOR: vf_module_name"


def test_base_parameters(base):
    params = base["input"]["preload-vf-module-topology-information"][
        "vf-module-topology"
    ]["vf-module-parameters"]["param"]
    assert params == [
        {"name": "svc_image_name", "value": "svc_image"},
        {"name": "svc_flavor_name", "value": "svc_flavor"},
    ]


def test_incremental(incremental):
    az = incremental["input"]["preload-vf-module-topology-information"][
        "vnf-resource-assignments"
    ]["availability-zones"]["availability-zone"]
    assert isinstance(az, list)
    assert len(az) == 1
    assert az[0] == "VALUE FOR: availability_zone_0"


def test_incremental_networks(incremental):
    nets = incremental["input"]["preload-vf-module-topology-information"][
        "vnf-resource-assignments"
    ]["vnf-networks"]["vnf-network"]
    assert isinstance(nets, list)
    assert len(nets) == 1
    assert nets[0]["network-role"] == "ha"


def test_preload_env_population(preload):
    base_path = THIS_DIR / "sample_env/preloads/grapi/base.json"
    data = load_json(base_path)
    azs = data["input"]["preload-vf-module-topology-information"][
        "vnf-resource-assignments"
    ]["availability-zones"]["availability-zone"]
    assert azs == ["az0", "az1"]
