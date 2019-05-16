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
#
import os

from tests.helpers import get_base_template_from_yaml_files
from tests.utils.nested_files import get_nested_files


def is_incremental_module(yaml_file, yaml_files):
    """
    Returns true if the file is not a base module, volume module, or nested module.
    """
    base_template = get_base_template_from_yaml_files(yaml_files)
    nested_templates = get_nested_files(yaml_files)
    is_volume_module = os.path.splitext(yaml_file)[0].endswith("_volume")
    return (
        yaml_file != base_template
        and yaml_file not in nested_templates
        and not is_volume_module
    )


def get_incremental_modules(yaml_files):
    """
    Returns the a list of file paths for the incremental modules in yaml_files
    """
    return [f for f in yaml_files if is_incremental_module(f, yaml_files)]
