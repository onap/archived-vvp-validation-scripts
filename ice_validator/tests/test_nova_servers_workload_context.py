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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

"""workload context
"""

import pytest
from tests import cached_yaml as yaml

from .helpers import validates

VERSION = "1.0.0"


@validates("R-74978")
def test_workload_context(heat_template):
    """
    A VNF's Heat Orchestration Template's OS::Nova::Server Resource
    **MUST**
    contain the metadata map value parameter 'workload_context'.

    A VNF's Heat Orchestration Template's OS::Nova::Server Resource
    metadata map value parameter 'workload_context' **MUST**
    be declared as type: 'string'.
    """
    with open(heat_template) as fh:
        yml = yaml.load(fh)

    if "parameters" not in yml:
        pytest.skip("No parameters specified in the heat template")
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    for resource, v in yml["resources"].items():
        if (
            not isinstance(v, dict)
            or v.get("type") != "OS::Nova::Server"
            or "properties" not in v
        ):
            continue
        metadata = v["properties"].get("metadata")
        if not isinstance(metadata, dict):
            continue
        error = validate_metadata(metadata, yml["parameters"])
        if error:
            assert False, '%s resource "%s" %s' % (heat_template, resource, error)


def validate_metadata(metadata, parameters):
    """validate metatdata.
    Ensure metadata references parameter workload_context,
    and that it is a string.
    Return error message string or None if no errors.
    """
    for value in metadata.values():
        if isinstance(value, dict):
            if "get_param" in value:
                if value["get_param"] == "workload_context":
                    wc = parameters.get("workload_context", {})
                    if wc.get("type") == "string":
                        break
                    else:
                        return (
                            'must have parameter "workload_context"' ' of type "string"'
                        )
                    break
    else:
        return None
