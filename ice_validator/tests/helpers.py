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

"""Helpers
"""

import os
import re
from collections import defaultdict

from boltons import funcutils
from tests import cached_yaml as yaml

VERSION = "1.1.0"


def check_basename_ending(template_type, basename):
    """
    return True/False if the template type is matching
    the filename
    """
    if not template_type:
        return True
    elif template_type == "volume":
        return basename.endswith("_volume")
    else:
        return not basename.endswith("_volume")


def get_parsed_yml_for_yaml_files(yaml_files, sections=None):
    """
    get the parsed yaml for a list of yaml files
    """
    sections = [] if sections is None else sections
    parsed_yml_list = []
    for yaml_file in yaml_files:
        try:
            with open(yaml_file) as fh:
                yml = yaml.load(fh)
        except yaml.YAMLError as e:
            # pylint: disable=superfluous-parens
            print("Error in %s: %s" % (yaml_file, e))
            continue
        if yml:
            if sections:
                for k in yml.keys():
                    if k not in sections:
                        del yml[k]
            parsed_yml_list.append(yml)
    return parsed_yml_list


def validates(*requirement_ids):
    """Decorator that tags the test function with one or more requirement IDs.

    Example:
        >>> @validates('R-12345', 'R-12346')
        ... def test_something():
        ...     pass
        >>> assert test_something.requirement_ids == ['R-12345', 'R-12346']
    """
    # pylint: disable=missing-docstring
    def decorator(func):
        # NOTE: We use a utility here to ensure that function signatures are
        # maintained because pytest inspects function signatures to inject
        # fixtures.  I experimented with a few options, but this is the only
        # library that worked. Other libraries dynamically generated a
        # function at run-time, and then lost the requirement_ids attribute
        @funcutils.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.requirement_ids = requirement_ids
        return wrapper

    decorator.requirement_ids = requirement_ids
    return decorator


def categories(*categories):
    def decorator(func):
        @funcutils.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.categories = categories
        return wrapper

    decorator.categories = categories
    return decorator


def get_environment_pair(heat_template):
    """Returns a yaml/env pair given a yaml file"""
    base_dir, filename = os.path.split(heat_template)
    basename = os.path.splitext(filename)[0]
    env_template = os.path.join(base_dir, "{}.env".format(basename))
    if os.path.exists(env_template):
        with open(heat_template, "r") as fh:
            yyml = yaml.load(fh)
        with open(env_template, "r") as fh:
            eyml = yaml.load(fh)

        environment_pair = {"name": basename, "yyml": yyml, "eyml": eyml}
        return environment_pair

    return None


def find_environment_file(yaml_files):
    """
    Pass file and recursively step backwards until environment file is found

    :param yaml_files: list or string, start at size 1 and grows recursively
    :return: corresponding environment file for a file, or None
    """
    # sanitize
    if isinstance(yaml_files, str):
        yaml_files = [yaml_files]

    yaml_file = yaml_files[-1]
    filepath, filename = os.path.split(yaml_file)

    environment_pair = get_environment_pair(yaml_file)
    if environment_pair:
        return environment_pair

    for file in os.listdir(filepath):
        fq_name = "{}/{}".format(filepath, file)
        if fq_name.endswith("yaml") or fq_name.endswith("yml"):
            if fq_name not in yaml_files:
                with open(fq_name) as f:
                    yml = yaml.load(f)
                resources = yml.get("resources", {})
                for resource_id, resource in resources.items():
                    resource_type = resource.get("type", "")
                    if resource_type == "OS::Heat::ResourceGroup":
                        resource_type = (
                            resource.get("properties", {})
                            .get("resource_def", {})
                            .get("type", "")
                        )
                    # found called nested file
                    if resource_type == filename:
                        yaml_files.append(fq_name)
                        environment_pair = find_environment_file(yaml_files)

    return environment_pair


def load_yaml(yaml_file):
    """
    Load the YAML file at the given path.  If the file has previously been
    loaded, then a cached version will be returned.

    :param yaml_file: path to the YAML file
    :return: data structure loaded from the YAML file
    """
    with open(yaml_file) as fh:
        return yaml.load(fh)


def traverse(data, search_key, func, path=None):
    """
    Traverse the data structure provided via ``data`` looking for occurences
    of ``search_key``.  When ``search_key`` is found, the value associated
    with that key is passed to ``func``

    :param data:        arbitrary data structure of dicts and lists
    :param search_key:  key field to search for
    :param func:        Callable object that takes two parameters:
                        * A list representing the path of keys to search_key
                        * The value associated with the search_key
    """
    path = [] if path is None else path
    if isinstance(data, dict):
        for key, value in data.items():
            curr_path = path + [key]
            if key == search_key:
                func(curr_path, value)
            traverse(value, search_key, func, curr_path)
    elif isinstance(data, list):
        for value in data:
            curr_path = path + [value]
            if isinstance(value, (dict, list)):
                traverse(value, search_key, func, curr_path)
            elif value == search_key:
                func(curr_path, value)


def check_indices(pattern, values, value_type):
    """
    Checks that indices associated with the matched prefix start at 0 and
    increment by 1.  It returns a list of messages for any prefixes that
    violate the rules.

    :param pattern: Compiled regex that whose first group matches the prefix and
                    second group matches the index
    :param values:  sequence of string names that may or may not match the pattern
    :param name:    Type of value being checked (ex: IP Parameters). This will
                    be included in the error messages.
    :return:        List of error messages, empty list if no violations found
    """
    if not hasattr(pattern, "match"):
        raise RuntimeError("Pattern must be a compiled regex")

    prefix_indices = defaultdict(set)
    for value in values:
        m = pattern.match(value)
        if m:
            prefix_indices[m.group(1)].add(int(m.group(2)))

    invalid_params = []
    for prefix, indices in prefix_indices.items():
        indices = sorted(indices)
        if indices[0] != 0:
            invalid_params.append(
                "{} with prefix {} do not start at 0".format(value_type, prefix)
            )
        elif len(indices) - 1 != indices[-1]:
            invalid_params.append(
                (
                    "Index values of {} with prefix {} do not " + "increment by 1: {}"
                ).format(value_type, prefix, indices)
            )
    return invalid_params


RE_BASE = re.compile(r"(^base$)|(^base_)|(_base_)|(_base$)")


def get_base_template_from_yaml_files(yaml_files):
    """Return first filepath to match RE_BASE
    """
    for filepath in yaml_files:
        basename = get_base_template_from_yaml_file(filepath)
        if basename:
            return basename
    return None


def get_base_template_from_yaml_file(yaml_file):
    (dirname, filename) = os.path.split(yaml_file)
    files = os.listdir(dirname)
    for file in files:
        basename, __ = os.path.splitext(os.path.basename(file))
        if (
            (__ == ".yaml" or __ == ".yml")
            and RE_BASE.search(basename)
            and basename.find("volume") == -1
        ):
            return os.path.join(dirname, "{}{}".format(basename, __))
    return None


def parameter_type_to_heat_type(parameter):
    # getting parameter format
    if isinstance(parameter, list):
        parameter_type = "comma_delimited_list"
    elif isinstance(parameter, str):
        parameter_type = "string"
    elif isinstance(parameter, dict):
        parameter_type = "json"
    elif isinstance(parameter, int):
        parameter_type = "number"
    elif isinstance(parameter, float):
        parameter_type = "number"
    elif isinstance(parameter, bool):
        parameter_type = "boolean"
    else:
        parameter_type = None

    return parameter_type


def prop_iterator(resource, *props):
    terminators = ["get_resource", "get_attr", "str_replace", "get_param"]
    if "properties" in resource:
        resource = resource.get("properties")
    props = list(props)

    if isinstance(resource, dict) and any(x for x in terminators if x in resource):
        yield resource
    else:
        prop = resource.get(props.pop(0))
        if isinstance(prop, list):
            for x in prop:
                yield from prop_iterator(x, *props)
        elif isinstance(prop, dict):
            yield from prop_iterator(prop, *props)


def get_param(property_value):
    """
    Returns the first parameter name from a get_param or None if get_param is
    not used
    """
    if property_value and isinstance(property_value, dict):
        param = property_value.get("get_param")
        if param and isinstance(param, list) and len(param) > 0:
            return param[0]
        else:
            return param
    return None
