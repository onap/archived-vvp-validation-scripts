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
import os

from tests.helpers import validates
from tests.utils.incrementals import is_incremental_module

from tests.structures import Heat


@validates("R-610030")
def test_incremental_module_has_server(yaml_files):
    modules = (f for f in yaml_files if is_incremental_module(f, yaml_files))
    errors = []
    for module in modules:
        servers = Heat(filepath=module).get_resource_by_type(
            "OS::Nova::Server", all_resources=True
        )
        volumes = Heat(filepath=module).get_resource_by_type(
            "OS::Cinder::Volume", all_resources=True
        )
        if not (servers or volumes):
            errors.append(os.path.basename(module))

    assert not errors, (
        "The following incremental modules do not contain at least one "
        "OS::Nova::Server or OS::Cinder::Volume "
        "as required: {}".format(", ".join(errors))
    )
