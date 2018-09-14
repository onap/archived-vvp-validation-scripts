# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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
import glob
import os

import pytest
from tests import cached_yaml as yaml

from .helpers import validates


def expected_template_module_pair(volume_path):
    """Returns the path to the expected base or incremental module for a given volume"""
    base_dir, filename = os.path.split(volume_path)
    return os.path.join(base_dir, filename.replace("_volume", ""))


@validates("R-82732")
def test_volume_module_name_matches_incremental_or_base_module(volume_template):
    expected_template_name = expected_template_module_pair(volume_template)
    assert os.path.exists(
        expected_template_name
    ), "Could not find corresponding module ({}) for volume module ({}".format(
        expected_template_name, volume_template
    )


@validates("R-11200", "R-07443")
def test_volume_outputs_consumed(template_dir, volume_template):
    """
    Check that all outputs in a volume template is consumed
    by the corresponding heat template
    """
    pair_template = expected_template_module_pair(volume_template)

    # Make sure all the output parameters in the volume module are
    # consumed by the expected base or incremental module
    if not os.path.exists(pair_template):
        pytest.skip("Expected pair module not found")
    with open(volume_template, "r") as f:
        volume = yaml.load(f)
    with open(pair_template, "r") as f:
        pair = yaml.load(f)
    outputs = set(volume.get("outputs", {}).keys())
    parameters = set(pair.get("parameters", {}).keys())
    missing_output_parameters = outputs.difference(parameters)
    assert not missing_output_parameters, (
        "The output parameters ({}) in {} were not all "
        "used by the expected module {}".format(
            ",".join(missing_output_parameters), volume_template, pair_template
        )
    )

    # Now make sure that none of the output parameters appear in any other
    # template
    template_files = set(glob.glob("*.yaml"))
    errors = {}
    for template_path in template_files:
        if template_path in (pair_template, volume_template):
            continue  # Skip these files since we already checked this pair
        with open(template_path, "r") as f:
            template = yaml.load(f)
        parameters = set(template.get("parameters", {}).keys())
        misused_outputs = outputs.intersection(parameters)
        if misused_outputs:
            errors[template_path] = misused_outputs
    message = ", ".join(
        "{} ({})".format(path, ", ".join(params)) for path, params in errors.items()
    )
    assert not errors, "Volume output parameters detected in unexpected modules: " + \
                       message
