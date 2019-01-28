# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2019 AT&T Intellectual Property. All rights reserved.
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
import os
from .helpers import validates
from .utils.vm_types import get_all_vm_types
from .parametrizers import get_nested_files

VERSION = "1.0.0"

# pylint: disable=invalid-name


@validates("R-70276")
def test_filename_is_vmtype_dot_yaml(yaml_files):

    vm_types = []
    invalid_files = []
    nested_files = []

    nested_files.extend(
        os.path.splitext(os.path.basename(filename))[0]
        for filename in get_nested_files(yaml_files)
    )

    vm_types = get_all_vm_types(yaml_files)

    invalid_files.extend(vm_type for vm_type in vm_types if vm_type in nested_files)

    assert (
        not invalid_files
    ), "Nested filenames must not be in format vm_type.yaml: {}".format(invalid_files)
