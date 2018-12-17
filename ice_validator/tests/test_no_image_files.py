# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2018 AT&T Intellectual Property. All rights reserved.
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


INVALID_EXTS = {
    ".aki",
    ".ami",
    ".ari",
    ".iso",
    ".qcow2",
    ".raw",
    ".vdi",
    ".vhd",
    ".vhdx",
    ".vmdk",
    ".bare",
    ".ova",
    ".ovf",
    ".docker",
}


@validates("R-348813")
def test_no_image_files_included(template_dir):
    filenames = (f.lower() for f in os.listdir(template_dir))
    exts = {os.path.splitext(f)[1] for f in filenames}
    bad_exts = exts.intersection(INVALID_EXTS)
    msg = (
        "Image files are not allowed in the template package.  Files with "
        + "the following extensions were found: {}".format(", ".join(bad_exts))
    )
    assert not bad_exts, msg
