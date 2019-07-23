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
#

from io import StringIO

import pytest
import yaml

import vvp

DEFAULT_CONFIG = """
ui:
  app-name: VNF Validation Tool
categories:
  - name: Environment File Compliance. (Required to Onboard)
    category: environment_file
    description:
      Checks certain parameters are excluded from the .env file, per HOT Requirements.
      Required for ASDC onboarding, not needed for manual Openstack testing.
settings:
  polling-freqency: 1000
  default-verbosity: Standard
"""


# noinspection PyShadowingNames
@pytest.fixture(scope="module")
def config():
    return vvp.Config(yaml.safe_load(StringIO(DEFAULT_CONFIG)))


def test_app_name(config):
    assert "VNF Validation Tool" in config.app_name
    assert vvp.VERSION in config.app_name


def test_categories_names_length(config):
    names = config.category_names
    assert len(names) == 1
    assert names[0] == "Environment File Compliance. (Required to Onboard)"


def test_polling_frequency(config):
    assert config.polling_frequency == 1000


def test_get_category_when_other(config):
    assert (
        config.get_category("Environment File Compliance. (Required to Onboard)")
        == "environment_file"
    )


def test_default_verbosity(config):
    assert config.default_verbosity(vvp.ValidatorApp.VERBOSITY_LEVELS) == "Standard (-v)"


def test_queues(config):
    assert config.log_queue.empty(), "Log should start empty"
    config.log_file.write("Test")
    assert config.log_queue.get() == "Test"

    assert config.status_queue.empty(), "status should start empty"
    config.status_queue.put((True, None))
    assert config.status_queue.get() == (True, None)


MISSING_CATEGORY_FIELD = """
ui:
  app-name: VNF Validation Tool
categories:
  - description: |
      Runs all default validations that apply to all VNF packages
      regardless of deployment environment
settings:
  polling-freqency: 1000
"""


def test_missing_category_fields():
    settings = yaml.safe_load(StringIO(MISSING_CATEGORY_FIELD))
    with pytest.raises(RuntimeError) as e:
        vvp.Config(settings)
    assert "Missing: name" in str(e)


def test_default_output_format(config):
    assert config.default_report_format == "HTML"


def test_output_formats(config):
    for format in ["CSV", "HTML", "Excel"]:
        assert format in config.report_formats


def test_category_names(config):
    assert "Environment File Compliance. (Required to Onboard)" in config.category_names


def test_default_input_format(config):
    assert "Directory (Uncompressed)" == config.default_input_format


def test_input_formats(config):
    assert "Directory (Uncompressed)" in config.input_formats
    assert "ZIP File" in config.input_formats
