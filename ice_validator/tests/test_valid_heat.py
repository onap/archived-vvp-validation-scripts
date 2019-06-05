# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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
import mock
import os
import pytest

from heat.common import template_format
from heat.engine import resources
from heat.engine import service
from heat.tests.openstack.nova import fakes as fakes_nova
from heat.tests import utils

from tests import cached_yaml as yaml
from tests.utils.nested_files import get_list_of_nested_files
from tests.helpers import categories, validates


def load_file(filename, file_cache):
    basename = os.path.basename(filename)
    if basename not in file_cache:
        with open(filename, "r") as fh:
            file_cache[basename] = fh.read()

    return file_cache[basename]


def generate_parameters(yml_data):
    parameters = yml_data.get("parameters", {})
    dummy_params = {}

    for p, v in parameters.items():
        param_type = v.get("type", "")
        if param_type == "comma_delimited_list":
            param = "1,2,3"
        elif param_type == "string":
            param = "123"
        elif param_type == "json":
            param = {"abc": "123"}
        elif param_type == "number":
            param = 123
        elif param_type == "boolean":
            param = True
        else:
            param = "123"
        dummy_params[p] = param

    return {"parameters": dummy_params}


class HOTValidator:
    def __init__(self, yaml_file, files, yml_data):
        resources.initialise()
        self.fc = fakes_nova.FakeClient()
        self.gc = fakes_nova.FakeClient()
        resources.initialise()
        self.ctx = utils.dummy_context()
        self.mock_isa = mock.patch(
            "heat.engine.resource.Resource.is_service_available",
            return_value=(True, None),
        )
        self.mock_is_service_available = self.mock_isa.start()
        self.engine = service.EngineService("a", "t")

        self.yaml_file = yaml_file
        self.files = files
        self.yml_data = yml_data

    def validate_heat(self):
        ymldata = load_file(self.yaml_file, self.files)
        parameters = generate_parameters(self.yml_data)

        t = template_format.parse(ymldata)

        try:
            res = dict(
                self.engine.validate_template(
                    self.ctx, t, files=self.files, params=parameters, show_nested=False
                )
            )
        except Exception as e:
            res = {"Error": e.__context__}

        if isinstance(res, dict) and "Error" in res:
            return res.get("Error")
        else:
            return None


@validates("R-92635")
@categories("openstack")
def test_heat(yaml_file):
    with open(yaml_file, "r") as f:
        yml = yaml.load(f)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    files = {}
    dirname = os.path.dirname(yaml_file)
    for file in set(get_list_of_nested_files(yaml_file, dirname)):
        load_file(file, files)

    validator = HOTValidator(yaml_file, files, yml)
    msg = validator.validate_heat()

    assert not msg, "Invalid OpenStack Heat detected in {}: {}".format(
        os.path.basename(yaml_file), msg
    )
