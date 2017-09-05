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

from os import path, sep
import yaml
import pytest


def test_base_template_outputs_consumed(heat_templates):
    '''
    Check that all outputs in the base template is consumed
    by another template. The exception is the predefined output
    parameters.
    '''
    base_template = ""
    base_template_yml = ""
    for heat_template in heat_templates:
        with open(heat_template) as fh:
            yml = yaml.load(fh)
        basename = path.splitext(heat_template)[0].rsplit(sep, 1)[1]
        if (basename.endswith("_base") or
                basename.startswith("base_") or
                basename.find("_base_") > 0):
                base_template = heat_template
                base_template_yml = yml

    # get the base template outputs
    if "outputs" not in base_template_yml:
        pytest.skip("No outputs specified in the base template")

    predefined_outputs = ['oam_management_v4_address',
                          'oam_management_v6_address']
    base_outputs = set(base_template_yml["outputs"]) - set(predefined_outputs)

    # get all add-on templates
    addon_heat_templates = set(heat_templates) - set([base_template])

    # get all parameters from add-on templates
    non_base_parameters = []
    for addon_heat_template in addon_heat_templates:
        with open(addon_heat_template) as fh:
            yml = yaml.load(fh)
        if "parameters" not in yml:
            continue
        parameters = yml["parameters"].keys()
        non_base_parameters.extend(parameters)

    assert base_outputs <= set(non_base_parameters)
