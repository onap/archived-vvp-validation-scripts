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

import uuid
from io import StringIO

import pytest
import yaml

from config import Config, to_uri
import vvp
from preload.engine import PLUGIN_MGR

DEFAULT_CONFIG = """
namespace: {namespace}
owner: onap-test
ui:
  app-name: VNF Validation Tool
  requirement-link-url: http://requirement.url.com
categories:
  - name: Environment File Compliance. (Required to Onboard)
    category: environment_file
    description:
      Checks certain parameters are excluded from the .env file, per HOT Requirements.
      Required for ASDC onboarding, not needed for manual Openstack testing.
settings:
  polling-freqency: 1000
  env-specs:
  - tests.test_environment_file_parameters.ENV_PARAMETER_SPEC
terms:
    version: 1.0.0
    path: path/to/terms.txt
    popup-title: Terms and Conditions
    popup-link-text: View Terms and Conditions
    popup-msg-text: Review and Accept the Terms
"""


# noinspection PyShadowingNames
@pytest.fixture()
def config():
    unique = str(uuid.uuid4())
    data = DEFAULT_CONFIG.format(namespace=unique)
    return Config(yaml.safe_load(StringIO(data)))


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


def test_queues(config):
    assert config.log_queue.empty(), "Log should start empty"
    config.log_file.write("Test")
    assert config.log_queue.get() == "Test"

    assert config.status_queue.empty(), "status should start empty"
    config.status_queue.put((True, None))
    assert config.status_queue.get() == (True, None)


MISSING_CATEGORY_FIELD = """
namespace: org.onap.test
owner: onap-test
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
        Config(settings)
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


def test_env_specs(config):
    specs = config.env_specs
    assert len(specs) == 1
    assert "ALL" in specs[0]


def test_get_generator_plugin_names(config):
    names = [g.format_name() for g in PLUGIN_MGR.preload_generators]
    assert "VNF-API" in names
    assert "GR-API" in names


def test_preload_formats(config):
    formats = config.preload_formats
    assert all(format in formats for format in ("VNF-API", "GR-API"))


def test_requirement_link_http(config):
    assert config.requirement_link_url == "http://requirement.url.com"


def test_to_uri_relative_path():
    assert to_uri("path/").startswith("file://")
    assert to_uri("path/").endswith("/path")


def test_to_uri_relative_http():
    assert to_uri("http://url.com") == "http://url.com"


def test_to_uri_absolute_path():
    assert to_uri("/path/one").startswith("file:///")
    assert to_uri("/path/one").endswith("/path/one")


def test_requirement_link_path(config):
    config._config["ui"]["requirement-link-url"] = "path/to/reqs.txt"
    url = config.requirement_link_url
    assert url.startswith("file://")
    assert "path/to/reqs.txt" in url


def test_terms_version(config):
    assert config.terms_version == "1.0.0"


def test_terms_popup_title(config):
    assert config.terms_popup_title == "Terms and Conditions"


def test_terms_popup_message(config):
    assert config.terms_popup_message == "Review and Accept the Terms"


def test_terms_link_url_default(config):
    config._config["terms"]["path"] = None
    assert config.terms_link_url is None


def test_terms_acceptance(config):
    assert not config.are_terms_accepted
    config.set_terms_accepted()
    assert config.are_terms_accepted


def test_terms_link_url_path(config):
    assert config.terms_link_url.startswith("file://")
    assert config.terms_link_url.endswith("/path/to/terms.txt")


def test_terms_link_text(config):
    assert config.terms_link_text == "View Terms and Conditions"


def test_default_halt_on_failure(config):
    assert config.default_halt_on_failure


def test_get_subdir_for_preload(config):
    assert config.get_subdir_for_preload("VNF-API") == "vnfapi"


def test_default_preload_format(config):
    assert config.default_preload_format in ("VNF-API", "GR-API", "Excel")


def test_category_description(config):
    assert "Checks certain parameters" in config.get_description(
        "Environment File Compliance. (Required to Onboard)"
    )


def test_get_category_by_name(config):
    assert (
        config.get_category("Environment File Compliance. (Required to Onboard)")
        == "environment_file"
    )


def test_cached_category_setting(config):
    assert (
        config.get_category_value("Environment File Compliance. (Required to Onboard)")
        == 0
    )


def test_disclaimer_text(config):
    assert config.disclaimer_text == ""


def test_requirement_link_text(config):
    url_text = "Requirement URL"
    config._config["ui"]["requirement-link-text"] = url_text
    assert config.requirement_link_text == url_text
