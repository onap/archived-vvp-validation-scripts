# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the “License”);
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
# under the Creative Commons License, Attribution 4.0 Intl. (the “License”);
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


def test_required_parameters_provided_in_env_file(environment_pair):
    '''
    Make sure all required parameters are specified properly
    in the environment file if a server is defined in the
    corresponding heat template
    '''
    required_parameters = ["vnf_id", "vf_module_id", "vnf_name"]

    if "resources" not in environment_pair["yyml"]:
        pytest.skip("No resources specified in the heat template")

    if "parameters" not in environment_pair["eyml"]:
        pytest.skip("No parameters specified in the environment file")

    server_count = 0
    for v in environment_pair["yyml"]['resources'].values():
        if "type" not in v:
            continue
        if v["type"] == "OS::Nova::Server":
            server_count += 1

    if server_count == 0:
        pytest.skip("No Nova Server resources specified in " +
                    "the heat template")

    provided_parameters = []
    for k in environment_pair["eyml"]['parameters']:
        if k in required_parameters:
            provided_parameters.append(k)

    assert set(required_parameters) == set(provided_parameters)
