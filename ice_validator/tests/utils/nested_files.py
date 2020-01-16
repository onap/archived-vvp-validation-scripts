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

from functools import lru_cache
from os import path, listdir
import re
from tests import cached_yaml as yaml

from tests.helpers import load_yaml

MAX_DEPTH = 2


def check_for_invalid_nesting(  # pylint: disable=too-many-branches
    yml, yaml_file, dirpath
):
    """
    return a list of all nested files
    """
    if not hasattr(yml, "items"):
        return []
    invalid_nesting = []
    p = re.compile("^[A-z]*::[A-z]*::[A-z]*$")

    for v in yml.values():
        if isinstance(v, dict) and "type" in v:
            t = v["type"]
            if t.lower().endswith(".yml") or t.lower().endswith(".yaml"):
                filepath = path.join(dirpath, t)
            elif t == "OS::Heat::ResourceGroup":
                rd = v["properties"]["resource_def"]
                if not isinstance(rd, dict) or "type" not in rd:
                    invalid_nesting.append(yaml_file)
                    continue
                elif not p.match(rd["type"]):
                    filepath = path.join(dirpath, rd["type"])
                else:
                    continue
            else:
                continue
            try:
                with open(filepath) as fh:
                    yml = yaml.load(fh)
            except yaml.YAMLError as e:
                invalid_nesting.append(filepath)
                print(e)  # pylint: disable=superfluous-parens
            invalid_nesting.extend(check_for_invalid_nesting(yml, filepath, dirpath))
        if isinstance(v, dict):
            invalid_nesting.extend(check_for_invalid_nesting(v, yaml_file, dirpath))
        elif isinstance(v, list):
            for d in v:
                invalid_nesting.extend(check_for_invalid_nesting(d, yaml_file, dirpath))
    return invalid_nesting


@lru_cache(maxsize=None)
def get_list_of_nested_files(yml_path, dirpath):
    """
    return a list of all nested files
    """

    yml = load_yaml(yml_path)
    nested_files = []
    resources = yml.get("resources") or {}

    for v in resources.values():
        if isinstance(v, dict) and "type" in v:
            t = v["type"]
            if t.endswith(".yml") or t.endswith(".yaml"):
                filepath = path.join(dirpath, t)
                if path.exists(filepath):
                    nested_files.append(filepath)
                    nested_files.extend(get_list_of_nested_files(filepath, dirpath))
            elif t == "OS::Heat::ResourceGroup":
                rdt = v.get("properties", {}).get("resource_def", {}).get("type", None)
                if rdt and (rdt.endswith(".yml") or rdt.endswith(".yaml")):
                    filepath = path.join(dirpath, rdt)
                    if path.exists(filepath):
                        nested_files.append(filepath)
                        nested_files.extend(get_list_of_nested_files(filepath, dirpath))
    return nested_files


def get_resourcegroup_nested_files(yml, dirpath):
    """
    return a dict.
    key: key in yml which references a nested ResourceGroup file.
        (resource->type is ResourceGroup
            and resource->properties->resource_def->type is a yaml file)
    value: the nested file name.

    The keys are assumed to be unique across files.
    A separate test checks for that.
    """

    if not hasattr(yml, "get"):
        return {}

    nested_files = {}
    for rid, r in yml.get("resources", {}).items():
        if isinstance(r, dict) and "type" in r:
            t = r["type"]
            nested_file = None
            if t == "OS::Heat::ResourceGroup":
                rdt = r.get("properties", {}).get("resource_def", {}).get("type", None)
                if rdt and (rdt.endswith(".yml") or rdt.endswith(".yaml")):
                    nested_file = rdt
            if nested_file:
                filepath = path.join(dirpath, nested_file)
                if path.exists(filepath):
                    nested_files[rid] = nested_file
    return nested_files


def get_type_nested_files(yml, dirpath):
    """
    return a dict.
    key: key in yml which references a nested type file.
        (the resource "type" is a yaml file.)
    value: the nested file name.

    The keys are assumed to be unique across files.
    A separate test checks for that.
    """

    if not hasattr(yml, "get"):
        return {}

    nested_files = {}
    for rid, r in yml.get("resources", {}).items():
        if isinstance(r, dict) and "type" in r:
            t = r["type"]
            nested_file = None
            if t.endswith(".yml") or t.endswith(".yaml"):
                nested_file = t
            if nested_file:
                filepath = path.join(dirpath, nested_file)
                if path.exists(filepath):
                    nested_files[rid] = nested_file
    return nested_files


def get_nested_files(filenames):
    """
    returns all the nested files for a set of filenames
    """
    nested_files = []
    for filename in filenames:
        if file_is_a_nested_template(filename):
            nested_files.append(filename)
    return nested_files


@lru_cache(maxsize=None)
def file_is_a_nested_template(file):
    directory = path.dirname(file)
    nested_files = []
    for filename in listdir(directory):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filename = "{}/{}".format(directory, filename)
            try:
                nested_files.extend(
                    get_list_of_nested_files(filename, path.dirname(filename))
                )
            except yaml.YAMLError as e:
                print(e)  # pylint: disable=superfluous-parens
                continue
    return file in nested_files
