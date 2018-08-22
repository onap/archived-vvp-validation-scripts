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

""" environment file structure
"""

import yaml
import pytest

from .helpers import validates

VERSION = "1.0.0"

# pylint: disable=invalid-name


def test_environment_structure(env_file):
    """
    Check that all environments files only have the allowed sections
    """
    key_values = [
        "parameters",
        "event_sinks",
        "encrypted_parameters",
        "parameter_merge_strategies",
    ]

    with open(env_file) as fh:
        yml = yaml.load(fh)
    assert [k for k in key_values if k in yml], "%s missing any of %s" % (
        env_file,
        key_values,
    )


@validates("R-03324")
def test_environment_file_contains_required_sections(env_file):
    """
    Check that all environments files only have the allowed sections
    """
    required_keys = ["parameters"]

    with open(env_file) as fh:
        yml = yaml.load(fh)
    missing_keys = [v for v in required_keys if v not in yml]
    assert not missing_keys, "%s missing %s" % (env_file, missing_keys)


def test_environment_file_sections_have_the_right_format(env_file):
    """
    Check that all environment files have sections of the right format.
    Do note that it only tests for dicts or not dicts currently.
    """
    dict_keys = ["parameters", "encrypted_parameters", "parameter_merge_strategies"]
    not_dict_keys = ["event_sinks"]

    with open(env_file) as fh:
        yml = yaml.load(fh)

    if not [k for k in dict_keys + not_dict_keys if k in yml]:
        pytest.skip("The fixture is not applicable for this test")

    bad_dict_keys = [k for k in dict_keys if k in yml and not isinstance(yml[k], dict)]
    bad_not_dict_keys = [
        k for k in not_dict_keys if k in yml and isinstance(yml[k], dict)
    ]
    errors = []
    if bad_dict_keys:
        errors.append("must be dict %s" % bad_dict_keys)
    if bad_not_dict_keys:
        errors.append("must not be dict %s" % bad_not_dict_keys)
    assert not errors, "%s errors:\n    %s" % (env_file, "\n    ".join(errors))
