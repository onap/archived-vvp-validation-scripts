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

import yaml
from os import path
from .utils.nested_files import get_list_of_nested_files


def test_all_nested_templates_provided(yaml_files):
    '''
    Check that all templates marked as volume templates are
    in fact volume templates
    '''
    nested_yaml_files = []

    for yaml_file in yaml_files:
        with open(yaml_file) as fh:
            yml = yaml.load(fh)
        if "resources" not in yml:
            continue
        nested_yaml_files.extend(get_list_of_nested_files(
                yml["resources"], path.dirname(yaml_file)))

    # detect all provided nested files
    provided_nested_yaml_files = [f1
                                  for f1 in nested_yaml_files
                                  for f2 in yaml_files
                                  if f1 in f2]

    assert set(provided_nested_yaml_files) == set(nested_yaml_files)
