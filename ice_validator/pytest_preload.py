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

import importlib
import os
import shutil
import yaml

from tests.conftest import get_output_dir
from tests.parametrizers import parametrize_heat_templates

__path__ = [os.path.dirname(os.path.abspath(__file__))]

# Can be uesd to override the default preload creation module
def pytest_addoption(parser):
    parser.addoption(
        "--preload_module",
        dest="preload_module",
        action="store",
        help="Preload Module to use for Preload Creation",
    )

# This is only used to fake out parametrizers
class DummyMetafunc:
    def __init__(self, config):
        self.inputs = {}
        self.config = config

    def parametrize(self, name, file_list):
        self.inputs[name] = file_list


def pytest_sessionfinish(session, exitstatus):
    if exitstatus != 0:
        print("\n\nWARNING: Violations Detected. Preloads May Be Malformed.")
        # return

    if session.config.getoption("preload_module"):
        try:
            mod = session.config.getoption("preload_module")
            preload = importlib.import_module(mod)
        except ModuleNotFoundError:
            return
    else:
        return

    meta = DummyMetafunc(session.config)
    parametrize_heat_templates(meta)

    heat_templates = meta.inputs.get("heat_templates", [])

    if isinstance(heat_templates, list) and len(heat_templates) > 0:
        heat_templates = heat_templates[0]
    else:
        return

    for preload_format in ["vnfapi", "grapi"]:
        output_dir = "{}/preloads/{}".format(get_output_dir(session.config), preload_format)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        for template in heat_templates:
            preload.main(template, output_dir, preload_format=preload_format)
