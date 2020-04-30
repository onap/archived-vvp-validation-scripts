# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2020 AT&T Intellectual Property. All rights reserved.
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

from os import listdir
from os import path
import re
from pathlib import Path

import pytest

from .helpers import check_basename_ending
from .helpers import validates


RE_BASE = re.compile(r"(^base$)|(^base_)|(_base_)|(_base$)")


def list_filenames(template_dir):
    return [
        f
        for f in listdir(template_dir)
        if path.isfile(path.join(template_dir, f))
        and path.splitext(f)[-1] in [".yaml", ".yml"]
    ]


@validates("R-81339", "R-87247", "R-76057")
def test_template_names_valid_characters(template_dir):
    filenames = list_filenames(template_dir)
    errors = []
    for f in filenames:
        stem = Path(f).stem
        if not stem.replace("_", "").isalnum():
            errors.append(f)
    assert not errors, (
        "The following Heat template names include characters other than "
        "alphanumerics and underscores: {}"
    ).format(", ".join(errors))


@validates("R-37028", "R-87485", "R-81339", "R-87247", "R-76057")
def test_base_template_names(template_dir):
    """
    Check all base templates have a filename that includes "_base_".
    """
    filenames = list_filenames(template_dir)

    if not filenames and listdir(template_dir):
        pytest.skip("Nested directory detected.  Let that test fail instead.")

    base_modules = []
    for filename in filenames:
        basename = path.splitext(filename)[0]

        # volume templates are tied to their parent naming wise
        if check_basename_ending("volume", basename):
            continue

        if RE_BASE.search(basename.lower()):
            base_modules.append(filename)

    if not base_modules:
        msg = (
            "No base module detected in the following files "
            "from the template directory: {}"
        ).format(", ".join(filenames))
    elif len(base_modules) > 1:
        msg = (
            "Multiple base modules detected in the template "
            "directory, but only one is allowed: {}"
        ).format(", ".join(base_modules))
    else:
        msg = ""

    assert len(base_modules) == 1, msg
