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

"""heat parameters
"""

import os

import pytest
from tests import cached_yaml as yaml

from .helpers import validates
from .utils.nested_files import get_list_of_nested_files

VERSION = '1.0.0'


@validates('R-00011')
def test_nested_parameter(yaml_file):
    '''
    A VNF's Heat Orchestration Template's Nested YAML file's
    parameter's **MUST NOT** have a parameter constraint defined.

    '''
    with open(yaml_file) as fh:
        yml = yaml.load(fh)
    dirname = os.path.dirname(yaml_file)
    nested_files = get_list_of_nested_files(yml, dirname)
    if nested_files:
        for filename in nested_files:
            with open(filename) as fh:
                template = yaml.load(fh)
            parameters = template.get('parameters')
            if parameters and isinstance(parameters, dict):
                for param, value in parameters.items():
                    if isinstance(value, dict):
                        assert 'constraints' not in value, (
                            '%s parameter "%s" has "constraints"' % (
                                filename,
                                param))
    else:
        pytest.skip('No nested files')

