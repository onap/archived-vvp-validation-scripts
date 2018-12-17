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


class VolumePairModule:
    def __init__(self, volume_path):
        self.volume_path = volume_path

    @property
    def path_options(self):
        expected_path, _ = self.volume_path.rsplit("_volume", maxsplit=1)
        return (expected_path + ".yaml", expected_path + ".yml")

    @property
    def exists(self):
        return any(os.path.exists(option) for option in self.path_options)

    def get_module_path(self):
        """
        Return the path of the volume module's pair if it exists,
        otherwise None
        """
        for option in self.path_options:
            if os.path.exists(option):
                return option
        return None


@validates("R-82732")
def test_volume_module_name_matches_incremental_or_base_module(volume_template):
    pair_module = VolumePairModule(volume_template)
    assert pair_module.exists, (
        "Could not find a corresponding module ({}) for " + "volume module ({})"
    ).format(" or ".join(pair_module.path_options), volume_template)


@validates("R-11200", "R-07443")
def test_volume_outputs_consumed(template_dir, volume_template):
    """
    Check that all outputs in a volume template is consumed
    by the corresponding heat template
    """
    pair_module = VolumePairModule(volume_template)
    if not pair_module.exists:
        pytest.skip("No pair module found for volume template")
    with open(volume_template, "r") as f:
        volume = yaml.load(f)
    with open(pair_module.get_module_path(), "r") as f:
        pair = yaml.load(f)
    outputs = set(volume.get("outputs", {}).keys())
    parameters = set(pair.get("parameters", {}).keys())
    missing_output_parameters = outputs.difference(parameters)
    assert not missing_output_parameters, (
        "The output parameters ({}) in {} were not all "
        "used by the expected module {}".format(
            ",".join(missing_output_parameters), volume_template, pair_module
        )
    )

    # Now make sure that none of the output parameters appear in any other
    # template
    template_files = set(glob.glob("*.yaml")).union(glob.glob(".yml"))
    errors = {}
    for template_path in template_files:
        if template_path in (pair_module, volume_template):
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
    assert not errors, (
        "Volume output parameters detected in unexpected modules: " + message
    )
