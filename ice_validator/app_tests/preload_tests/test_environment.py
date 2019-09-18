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
from pathlib import Path

import pytest
from mock import mock

from preload.environment import CloudServiceArchive, PreloadEnvironment

THIS_DIR = Path(__file__).parent
PRELOAD_ENV_DIR = THIS_DIR / "preload_envs"


@pytest.fixture(scope="session")
def csar():
    return CloudServiceArchive(PRELOAD_ENV_DIR / "test.csar")


@pytest.fixture(scope="session")
def env():
    return PreloadEnvironment(PRELOAD_ENV_DIR)


def test_csar_service_name(csar):
    assert csar.service_name == "stark_0917_vlb_svc"


def test_csar_str_and_repr(csar):
    assert str(csar) == "CSAR (path=test.csar, name=stark_0917_vlb_svc)"
    assert repr(csar) == "CSAR (path=test.csar, name=stark_0917_vlb_svc)"


def test_csar_vf_module_model_name(csar):
    assert (
        csar.get_vf_module_model_name("vdns")
        == "Stark0917VlbVf..vdns..module-3"
    )


def test_csar_get_vf_module_resource_name(csar):
    assert csar.get_vf_module_resource_name("vdns") == "stark_0917_vlb_vf"


def test_csar_get_vnf_type(csar):
    assert csar.get_vnf_type("vdns") == "stark_0917_vlb_svc/stark_0917_vlb_vf"


def test_csar_get_vf_module_resource_name_not_found(csar):
    assert csar.get_vf_module_resource_name("unknown") is None


def test_preload_environment_global_csar(env):
    assert env.csar.service_name == "stark_0917_vlb_svc"


def test_preload_environment_nest_env_csar_inherit(env):
    env_two = env.get_environment("env_two")
    assert env_two.csar.service_name == "stark_0917_vlb_svc"


def test_preload_environment_nest_env_csar_override(env):
    sub_env = env.get_environment("env_three")
    assert sub_env.csar.service_name == "StarkMultiModule2_43550"


def test_preload_environment_environments(env):
    names = {e.name for e in env.environments}
    assert names == {"env_two", "env_three", "env_one_a"}


def test_preload_environment_environments_nested(env):
    env_one = env.get_environment("env_one")
    names = {e.name for e in env_one.environments}
    assert names == {"env_one_a"}


def test_preload_environment_get_module_global_base(env):
    module = env.get_module("base")
    assert module["my_ip"] == "default"


def test_preload_environment_get_module_global_not_found(env):
    module = env.get_module("unknown")
    assert module == {}


def test_preload_environment_get_module_sub_env(env):
    env_two = env.get_environment("env_two")
    module = env_two.get_module("base")
    assert module["my_ip"] == "192.168.0.2"
    assert module["common"] == "ABC"


def test_preload_environment_module_names(env):
    expected = {"base.env", "incremental.env"}
    assert env.module_names == expected
    # check a nested env with inherits all modules
    assert env.get_environment("env_three").module_names == expected


def test_preload_environment_modules(env):
    modules = env.modules
    assert isinstance(modules, dict)
    assert modules.keys() == {"base.env", "incremental.env"}
    assert all(isinstance(val, dict) for val in modules.values())


def test_preload_environment_is_base(env):
    assert env.is_base
    assert not env.get_environment("env_one").is_base


def test_preload_environment_is_leaf(env):
    assert not env.is_leaf
    assert env.get_environment("env_two").is_leaf
    assert not env.get_environment("env_one").is_leaf
    assert env.get_environment("env_one_a").is_leaf


def test_preload_environment_str_repr(env):
    assert str(env) == "PreloadEnvironment(name=preload_envs)"
    assert repr(env) == "PreloadEnvironment(name=preload_envs)"


def test_preload_environment_defaults(env):
    expected = {"availability_zone_0": "az0"}
    assert env.defaults == expected
    assert env.get_environment("env_one_a").defaults == expected


def test_preload_environment_defaults_merging_and_override(env):
    assert env.get_environment("env_three").defaults == {
        "availability_zone_0": "az0-b",
        "custom_env_3": "default",
    }


def test_preload_environment_defaults_in_module_env(env):
    mod = env.get_environment("env_three").get_module("base")
    assert mod == {
        "availability_zone_0": "az0-b",
        "common": "ABC",
        "custom_env_3": "default",
        "my_ip": "default",
    }
    mod = env.get_environment("env_one").get_module("base")
    assert mod == {
        "availability_zone_0": "az0",
        "common": "ABC",
        "my_ip": "192.168.0.1",
    }


def test_preload_environment_uses_csar(env, monkeypatch):
    csar = mock.MagicMock(spec=CloudServiceArchive)
    csar.get_vnf_type = mock.Mock(return_value="stark_vccf_svc/stark_vccf_vf")
    csar.get_vf_module_model_name = mock.Mock(return_value="model_name")
    env = env.get_environment("env_three")
    monkeypatch.setattr(env, "csar", csar)
    mod = env.get_module("base")
    assert mod["vnf-type"] == "stark_vccf_svc/stark_vccf_vf"
    assert mod["vf-module-model-name"] == "model_name"
