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

from os import listdir
from os import path
from .helpers import check_basename_ending


def test_base_template_names(template_dir):
    '''
    Check all base templates have a filename that includes "_base_".
    '''
    base_template_count = 0
    filenames = [f for f in listdir(template_dir)
                 if path.isfile(path.join(template_dir, f)) and
                 path.splitext(f)[-1] in ['.yaml', '.yml']]
    for filename in filenames:
        filename = path.splitext(filename)[0]

        # volume templates are tied to their parent naming wise
        if check_basename_ending('volume', filename):
            continue

        if (filename.endswith("_base") or
                filename.startswith("base_") or
                filename.find("_base_") > 0):
            base_template_count += 1
    assert base_template_count == 1
