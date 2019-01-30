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
#

import pytest
from tests import cached_yaml as yaml

from .helpers import validates


def check_parameters_no_constraints(yaml_file, parameter):

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    param = yml.get("parameters", {}).get(parameter)
    if not param:
        pytest.skip("Parameter {} not defined in parameters section".format(parameter))

    assert (
        "constraints" not in param
    ), "Found constraints defined for parameter: {}".format(parameter)


@validates("R-55218")
def test_vnf_id_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vnf_id")


@validates("R-98374")
def test_vf_module_id_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vf_module_id")


@validates("R-44318")
def test_vnf_name_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vnf_name")


@validates("R-34055")
def test_workload_context_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "workload_context")


@validates("R-56183")
def test_environment_context_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "environment_context")


@validates("R-15480")
def test_vf_module_name_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vf_module_name")


@validates("R-67597")
def test_vm_role_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vm_role")


@validates("R-09811")
def test_vf_module_index_parameter_has_no_constraints(yaml_file):
    check_parameters_no_constraints(yaml_file, "vf_module_index")
