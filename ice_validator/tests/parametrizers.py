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

"""parametrizers
"""

from os import path, listdir
import re
from tests import cached_yaml as yaml
import pytest
from tests.helpers import get_parsed_yml_for_yaml_files, check_basename_ending
from tests.utils.nested_files import get_nested_files

VERSION = "1.0.0"

# pylint: disable=invalid-name


def get_template_dir(metafunc):
    """
    returns template_dir, either as its passed in on CLI
    or, during --self-test, the directory whos name matches
    the current tests module name
    """
    if metafunc.config.getoption("template_dir", None) is None:
        return path.join(
            path.dirname(metafunc.module.__file__),
            "fixtures",
            metafunc.function.__module__.split(".")[-1],
        )
    else:
        return metafunc.config.getoption("template_dir")[0]


def list_filenames_in_template_dir(
    metafunc, extensions, template_type="", sub_dirs=None
):
    """
    returns the filenames in a template_dir, either as its passed in
    on CLI or, during --self-test, the directory whos name matches
    the current tests module name
    """
    sub_dirs = [] if sub_dirs is None else sub_dirs
    template_dir = get_template_dir(metafunc)
    filenames = []
    if metafunc.config.getoption("self_test"):
        filenames = [
            path.join(template_dir, s, f)
            for s in sub_dirs
            for f in listdir(path.join(template_dir, s))
            if path.isfile(path.join(template_dir, s, f))
            and path.splitext(f)[-1] in extensions
            and check_basename_ending(template_type, path.splitext(f)[0])
        ]
    else:
        filenames = [
            path.join(template_dir, f)
            for f in listdir(template_dir)
            if path.isfile(path.join(template_dir, f))
            and path.splitext(f)[-1] in extensions
            and check_basename_ending(template_type, path.splitext(f)[0])
        ]
    return filenames


def list_template_dir(
    metafunc, extensions, exclude_nested=True, template_type="", sub_dirs=None
):
    """
    returns the filenames excluding the nested files for a template_dir,
    either as its passed in on CLI or, during --self-test, the
    directory whos name matches the current tests module name
    """
    sub_dirs = [] if sub_dirs is None else sub_dirs
    filenames = []
    nested_files = []
    filenames = list_filenames_in_template_dir(
        metafunc, extensions, template_type, sub_dirs
    )
    if exclude_nested:
        nested_files = get_nested_files(filenames)
    return list(set(filenames) - set(nested_files))


def get_filenames_list(
    metafunc, extensions=None, exclude_nested=False, template_type=""
):
    """
    returns the filename fixtures for the template dir, either as by how its
    passed in on CLI or, during --self-test, the directory whos name
    matches the current tests module name
    """
    extensions = [".yaml", ".yml", ".env"] if extensions is None else extensions
    if metafunc.config.getoption("self_test"):
        filenames_list = list_template_dir(
            metafunc, extensions, exclude_nested, template_type, ["pass"]
        )
        filenames_list += [
            pytest.mark.xfail(f, strict=True)
            for f in list_template_dir(
                metafunc, extensions, exclude_nested, template_type, ["fail"]
            )
        ]
    else:
        filenames_list = list_template_dir(
            metafunc, extensions, exclude_nested, template_type
        )

    return filenames_list


def get_filenames_lists(
    metafunc, extensions=None, exclude_nested=False, template_type=""
):
    """
    returns the list of files in the template dir, either as by how its
    passed in on CLI or, during --self-test, the directory whos name
    matches the current tests module name
    """
    extensions = [".yaml", ".yml", ".env"] if extensions is None else extensions
    filenames_lists = []
    if metafunc.config.getoption("self_test", None):
        filenames_lists.append(
            list_template_dir(
                metafunc, extensions, exclude_nested, template_type, ["pass"]
            )
        )
        filenames_lists.append(
            pytest.mark.xfail(
                list_template_dir(
                    metafunc, extensions, exclude_nested, template_type, ["fail"]
                ),
                strict=True,
            )
        )
    else:
        filenames_lists.append(
            list_template_dir(metafunc, extensions, exclude_nested, template_type)
        )
    return filenames_lists


def get_parsed_yaml_files(
    metafunc, extensions, exclude_nested=True, template_type="", sections=None
):
    """
    returns the list of parsed yaml files in the specified template dir,
    either as by how its passed in on CLI or, during --self-test, the
    directory whos name matches the current tests module name
    """
    sections = [] if sections is None else sections
    extensions = [".yaml", ".yml"]

    if metafunc.config.getoption("self_test"):
        yaml_files = list_template_dir(
            metafunc, extensions, exclude_nested, template_type, ["pass"]
        )
        parsed_yml_list = get_parsed_yml_for_yaml_files(yaml_files, sections)

        yaml_files = list_template_dir(
            metafunc, extensions, exclude_nested, template_type, ["fail"]
        )
        parsed_yml_list = get_parsed_yml_for_yaml_files(yaml_files, sections)
        parsed_yml_list += [
            pytest.mark.xfail(parsed_yml, strict=True) for parsed_yml in parsed_yml_list
        ]
    else:
        yaml_files = list_template_dir(metafunc, extensions)
        parsed_yml_list = get_parsed_yml_for_yaml_files(yaml_files, sections)
    return parsed_yml_list


def parametrize_filenames(metafunc):
    """
    This param runs tests all files in the template dir
    """
    filenames = get_filenames_lists(metafunc)
    metafunc.parametrize("filenames", filenames)


def parametrize_filename(metafunc):
    """
    This param runs tests once for every file in the template dir
    """
    filenames = get_filenames_list(metafunc)
    metafunc.parametrize("filename", filenames)


def parametrize_yaml_files(metafunc):
    """
    This param runs tests for the yaml files in the template dir
    """
    yaml_files = get_filenames_lists(metafunc, [".yaml", ".yml"], False)
    metafunc.parametrize("yaml_files", yaml_files)


def parametrize_yaml_file(metafunc):
    """
    This param runs tests for every yaml file in the template dir
    """
    yaml_files = get_filenames_list(metafunc, [".yaml", ".yml"], False)
    metafunc.parametrize("yaml_file", yaml_files)


def parametrize_templates(metafunc):
    """
    This param runs tests for the template in the template dir
    """
    templates = get_filenames_lists(metafunc, [".yaml", ".yml"], True)
    metafunc.parametrize("templates", templates)


def parametrize_template(metafunc):
    """
    This param runs tests for every template in the template dir
    """
    templates = get_filenames_list(metafunc, [".yaml", ".yml"], True)
    metafunc.parametrize("template", templates)


def parametrize_parsed_yaml_file(metafunc):
    """
    This param runs tests for a parsed version of each yaml file
    in the template dir
    """
    parsed_yaml_files = get_parsed_yaml_files(metafunc, [".yaml", ".yml"], False)
    metafunc.parametrize("parsed_yaml_file", parsed_yaml_files)


def parametrize_heat_templates(metafunc):
    """
    This param runs tests for all heat templates in the template dir
    """
    heat_templates = get_filenames_lists(metafunc, [".yaml", ".yml"], True, "heat")
    metafunc.parametrize("heat_templates", heat_templates)


def parametrize_heat_template(metafunc):
    """
    This param runs tests for every heat template in the template dir
    """
    heat_templates = get_filenames_list(metafunc, [".yaml", ".yml"], True, "heat")
    metafunc.parametrize("heat_template", heat_templates)


def parametrize_volume_templates(metafunc):
    """
    This param runs tests for all volume templates in the template dir
    """
    volume_templates = get_filenames_lists(metafunc, [".yaml", ".yml"], True, "volume")
    metafunc.parametrize("volume_templates", volume_templates)


def parametrize_volume_template(metafunc):
    """

    This param runs tests for every volume template in the template dir
    """
    volume_templates = get_filenames_list(metafunc, [".yaml", ".yml"], True, "volume")
    metafunc.parametrize("volume_template", volume_templates)


def parametrize_environment_files(metafunc):
    """
    This param runs tests for all environment files in the template dir
    """
    env_files = get_filenames_lists(metafunc, [".env"])
    metafunc.parametrize("env_files", env_files)


def parametrize_environment_file(metafunc):
    """
    This param runs tests for every environment file in the template dir
    """
    env_files = get_filenames_list(metafunc, [".env"])
    metafunc.parametrize("env_file", env_files)


def parametrize_parsed_environment_file(metafunc):
    """
    This param runs tests for every parsed environment file
    in the template dir
    """
    parsed_env_files = get_parsed_yaml_files(metafunc, [".env"])
    metafunc.parametrize("parsed_env_file", parsed_env_files)


def parametrize_template_dir(metafunc):
    """
    This param passes a  the template_dir as passed in on CLI
    or, during --self-test, passes in the sub directories of
    template_dir/pass/ and template_dir/fail
    template_dir = get_template_dir(metafunc)
    """
    template_dir = get_template_dir(metafunc)

    if metafunc.config.getoption("self_test"):
        dirs = [
            path.join(template_dir, s, t)
            for s in ["pass"]
            for t in listdir(path.join(template_dir, s))
            if path.isdir(path.join(template_dir, s, t))
        ]

        dirs += [
            pytest.mark.xfail(path.join(template_dir, s, t))
            for s in ["fail"]
            for t in listdir(path.join(template_dir, s))
            if path.isdir(path.join(template_dir, s, t))
        ]
    else:
        dirs = [template_dir]

    metafunc.parametrize("template_dir", dirs)


def parametrize_environment_pair(metafunc, template_type=""):
    """
    Define a list of pairs of parsed yaml from the heat templates and
    environment files
    """
    pairs = []
    if metafunc.config.getoption("self_test"):
        sub_dirs = ["pass", "fail"]
        env_files = list_template_dir(metafunc, [".env"], True, template_type, sub_dirs)
        yaml_files = list_template_dir(
            metafunc, [".yaml", ".yml"], True, template_type, sub_dirs
        )
    else:
        env_files = list_template_dir(metafunc, [".env"], True, template_type)
        yaml_files = list_template_dir(metafunc, [".yaml", ".yml"], True, template_type)

    for filename in env_files:
        basename = path.splitext(filename)[0]
        if basename + ".yml" in yaml_files:
            yfilename = basename + ".yml"
        else:
            yfilename = basename + ".yaml"

        try:
            with open(filename) as fh:
                eyml = yaml.load(fh)
            with open(yfilename) as fh:
                yyml = yaml.load(fh)

            if "fail" in filename:
                pairs.append(
                    pytest.mark.xfail(
                        {"name": basename, "yyml": yyml, "eyml": eyml}, strict=True
                    )
                )
            else:
                pairs.append({"name": basename, "yyml": yyml, "eyml": eyml})

        except yaml.YAMLError as e:
            print(e)  # pylint: disable=superfluous-parens

    metafunc.parametrize("environment_pair", pairs)


def parametrize_heat_volume_pair(metafunc):
    """
    Define a list of pairs of parsed yaml from the a heat and volume
    template
    """
    pairs = []
    if metafunc.config.getoption("self_test"):
        sub_dirs = ["pass", "fail"]
        volume_files = list_template_dir(
            metafunc, [".yaml", ".yml"], True, "volume", sub_dirs
        )
        yaml_files = list_template_dir(metafunc, [".yaml", ".yml"], True, "", sub_dirs)
    else:
        volume_files = list_template_dir(metafunc, [".yaml", ".yml"], True, "volume")
        yaml_files = list_template_dir(metafunc, [".yaml", ".yml"], True)

    pattern = re.compile(r"\_volume$")
    for vfilename in volume_files:
        basename = pattern.sub("", path.splitext(vfilename)[0])
        if basename + ".yml" in yaml_files:
            yfilename = basename + ".yml"
        else:
            yfilename = basename + ".yaml"

        try:
            with open(vfilename) as fh:
                vyml = yaml.load(fh)
            with open(yfilename) as fh:
                yyml = yaml.load(fh)

            if "fail" in vfilename:
                pairs.append(
                    pytest.mark.xfail(
                        {"name": basename, "yyml": yyml, "vyml": vyml}, strict=True
                    )
                )
            else:
                pairs.append({"name": basename, "yyml": yyml, "vyml": vyml})

        except yaml.YAMLError as e:
            print(e)  # pylint: disable=superfluous-parens

    metafunc.parametrize("heat_volume_pair", pairs)
