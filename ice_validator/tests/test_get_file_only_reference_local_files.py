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
"""test get_file
"""
import re
from os import listdir
from os import path
from os import sep

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.nested_iterables import find_all_get_file_in_yml

VERSION = "1.0.0"

# pylint: disable=invalid-name


@validates("R-41888")
@pytest.mark.base
def test_get_file_no_url_retrieval(yaml_file):
    """
    Make sure that all references to get_file only try to access local files
    and only assume a flat directory structure
    """
    is_url = re.compile(r"(?:http|https|file|ftp|ftps)://.+")

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    get_files = find_all_get_file_in_yml(yml["resources"])

    invalid_files = []
    for get_file in get_files:
        if is_url.match(get_file):
            invalid_files.append(get_file)
            continue
        if sep in get_file:
            invalid_files.append(get_file)
            continue

    assert not set(invalid_files), "External get_file references detected {}".format(
        invalid_files
    )


@validates("R-76718")
@pytest.mark.base
def test_get_file_only_reference_local_files(yaml_file):
    """
    Make sure that all references to get_file only try to access local files
    and only assume a flat directory structure
    """
    is_url = re.compile(r"(?:http|https|file|ftp|ftps)://.+")
    base_dir, filename = path.split(yaml_file)

    with open(yaml_file) as fh:
        yml = yaml.load(fh)

    # skip if parameters are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    get_files = find_all_get_file_in_yml(yml["resources"])

    invalid_files = []
    for get_file in get_files:
        if is_url.match(get_file):
            pytest.skip("external get_file detected")
            continue
        if get_file not in listdir(base_dir):
            invalid_files.append(get_file)
            continue

    assert not set(invalid_files), "Non-local files detected in get_file {}".format(
        invalid_files
    )
