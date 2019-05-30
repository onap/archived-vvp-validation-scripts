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
import os

from tests.helpers import validates, traverse, load_yaml


def is_get_param(arg):
    return isinstance(arg, dict) and "get_param" in arg


class GetParamChecker:
    def __init__(self, yaml_file):
        self.errors = []
        self.filename = os.path.basename(yaml_file)

    def __call__(self, keys, param_value, *args, **kwargs):
        if isinstance(param_value, str):
            return  # refers to a string or parameter - this is OK
        if "outputs" in keys:
            return  # output section is exempt from this requirement
        if isinstance(param_value, list):
            nested_get_params = (arg for arg in param_value if is_get_param(arg))
            args = (call["get_param"] for call in nested_get_params)
            invalid_args = (arg for arg in args if not isinstance(arg, str))
            # We don't check if the args really point to parameters, because that
            # check is already covered by test_05_all_get_param_have_defined_parameter
            # in test_initial_configuration.py
            if any(invalid_args):
                self.errors.append(
                    (
                        "Invalid nesting of get_param detected in {} at {}. Calls to "
                        "get_param can only be nested two deep, and the argument to "
                        "the second get_param must only be a parameter name: {}"
                    ).format(
                        self.filename, " > ".join(keys), {"get_param": param_value}
                    )
                )


@validates("R-10834")
def test_nested_parameter_args(yaml_file):
    heat = load_yaml(yaml_file)
    checker = GetParamChecker(yaml_file)
    traverse(heat, "get_param", checker)
    assert not checker.errors, ". ".join(checker.errors)
