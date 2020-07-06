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

"""nested template parameters
"""
import os.path

import pytest

from .structures import Heat
from .helpers import validates
from .utils import nested_files

VERSION = "1.2.0"


def validate_parms(dirname, basename, nested, nested_props, prop_type):
    """ensure all parms are props
    return list of errors.
    """
    bad = []
    for rid, nested_filename in nested.items():
        nested_filepath = os.path.join(dirname, nested_filename)
        nested_heat = Heat(filepath=nested_filepath)
        parms = set(nested_heat.parameters.keys())
        props = nested_props.get(rid, set())
        missing = parms - props
        if missing:
            bad.append(
                "%s parameters %s missing as %s"
                " of %s resource %s"
                % (nested_filename, list(missing), prop_type, basename, rid)
            )
        else:
            additional = props - parms
            if additional:
                bad.append(
                    "%s properties %s not defined as "
                    "parameters in %s"
                    % (rid, list(additional), nested_filepath)
                )
    return bad


@validates("R-11041")
def test_nested_template_parameters(yaml_file):
    """
    All parameters defined in a VNFs Nested YAML file
    **MUST** be passed in as properties of the resource calling
    the nested yaml file.
    """
    dirname, basename = os.path.split(yaml_file)
    heat = Heat(filepath=yaml_file)
    if not heat.resources:
        pytest.skip("No resources found")
    nested_type = nested_files.get_type_nested_files(heat.yml, dirname)
    nested_resourcegroup = nested_files.get_resourcegroup_nested_files(
        heat.yml, dirname
    )
    if not nested_type and not nested_resourcegroup:
        pytest.skip("No nested files")
    bad = []
    nested_type_props = {
        rid: set(heat.resources[rid].get("properties", {}).keys())
        for rid in nested_type
    }
    nested_resourcegroup_props = {
        rid: set(
            heat.nested_get(
                heat.resources[rid],
                "properties",
                "resource_def",
                "properties",
                default={},
            ).keys()
        )
        for rid in nested_resourcegroup
    }
    bad.extend(
        validate_parms(dirname, basename, nested_type, nested_type_props, "properties")
    )
    bad.extend(
        validate_parms(
            dirname,
            basename,
            nested_resourcegroup,
            nested_resourcegroup_props,
            "resource_def.properties",
        )
    )
    assert not bad, "; ".join(bad)
