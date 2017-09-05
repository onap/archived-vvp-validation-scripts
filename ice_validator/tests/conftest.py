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

import os


__path__ = [os.path.dirname(os.path.abspath(__file__))]


def pytest_addoption(parser):
    """
    Add needed CLI arguments
    """
    parser.addoption("--template-directory",
                     dest="template_dir",
                     action="append",
                     help="Directory which holds the templates for validation")

    parser.addoption("--self-test",
                     dest="self_test",
                     action='store_true',
                     help="Test the unit tests against their fixtured data")


def pytest_configure(config):
    """
    Ensure that we are receive either `--self-test` or
    `--template-dir=<directory` as CLI arguments
    """
    if config.getoption('template_dir') and config.getoption('self_test'):
        raise Exception(('"--template-dir", and "--self-test"'
                        ' are mutually exclusive'))
    if not (config.getoption('template_dir') or config.getoption('self_test')):
        raise Exception(('One of "--template-dir" or'
                        ' "--self-test" must be specified'))


def pytest_generate_tests(metafunc):
    """
    If a unit test requires an argument named 'filename'
    we generate a test for the filenames selected. Either
    the files contained in `template_dir` or if `template_dir`
    is not specified on the CLI, the fixtures associated with this
    test name.
    """
    if 'filename' in metafunc.fixturenames:
        from .parametrizers import parametrize_filename
        parametrize_filename(metafunc)

    if 'filenames' in metafunc.fixturenames:
        from .parametrizers import parametrize_filenames
        parametrize_filenames(metafunc)

    if 'template_dir' in metafunc.fixturenames:
        from .parametrizers import parametrize_template_dir
        parametrize_template_dir(metafunc)

    if 'environment_pair' in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_pair
        parametrize_environment_pair(metafunc)

    if 'heat_volume_pair' in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_volume_pair
        parametrize_heat_volume_pair(metafunc)

    if 'yaml_files' in metafunc.fixturenames:
        from .parametrizers import parametrize_yaml_files
        parametrize_yaml_files(metafunc)

    if 'env_files' in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_files
        parametrize_environment_files(metafunc)

    if 'yaml_file' in metafunc.fixturenames:
        from .parametrizers import parametrize_yaml_file
        parametrize_yaml_file(metafunc)

    if 'env_file' in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_file
        parametrize_environment_file(metafunc)

    if 'parsed_yaml_file' in metafunc.fixturenames:
        from .parametrizers import parametrize_parsed_yaml_file
        parametrize_parsed_yaml_file(metafunc)

    if 'parsed_environment_file' in metafunc.fixturenames:
        from .parametrizers import parametrize_parsed_environment_file
        parametrize_parsed_environment_file(metafunc)

    if 'heat_template' in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_template
        parametrize_heat_template(metafunc)

    if 'heat_templates' in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_templates
        parametrize_heat_templates(metafunc)

    if 'volume_template' in metafunc.fixturenames:
        from .parametrizers import parametrize_volume_template
        parametrize_volume_template(metafunc)

    if 'volume_templates' in metafunc.fixturenames:
        from .parametrizers import parametrize_volume_templates
        parametrize_volume_templates(metafunc)

    if 'template' in metafunc.fixturenames:
        from .parametrizers import parametrize_template
        parametrize_template(metafunc)

    if 'templates' in metafunc.fixturenames:
        from .parametrizers import parametrize_templates
        parametrize_templates(metafunc)
