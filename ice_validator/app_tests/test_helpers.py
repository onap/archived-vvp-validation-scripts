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
from pathlib import Path

import pytest

from tests.helpers import check, first, unzip, remove

THIS_DIR = Path(__file__).parent


def test_check_fail():
    with pytest.raises(RuntimeError, match="pre-condition failed"):
        check(False, "pre-condition failed")


def test_check_pass():
    check(True, "pre-condition failed")


def test_first_found():
    result = first(range(1, 10), lambda x: x % 4 == 0)
    assert result == 4


def test_first_not_found():
    result = first(range(1, 3), lambda x: x % 4 == 0)
    assert result is None


def test_first_custom_default():
    result = first(range(1, 3), lambda x: x % 4 == 0, default="not found")
    assert result == "not found"


def test_unzip_success(tmpdir):
    test_zip = THIS_DIR / "test_data.zip"
    target_dir = tmpdir.join("sub-dir")
    unzip(test_zip, target_dir)
    assert "data.txt" in (p.basename for p in target_dir.listdir())


def test_unzip_not_found(tmpdir):
    test_zip = THIS_DIR / "test_data1.zip"
    with pytest.raises(RuntimeError, match="not a valid zipfile"):
        unzip(test_zip, tmpdir)


def test_remove_with_no_key():
    assert remove([1, 2, 3, 4], [3]) == [1, 2, 4]


def test_remove_with_key():
    assert remove(["a", "b", "c", "d"], ["A"], lambda s: s.upper()) == ["b", "c", "d"]
