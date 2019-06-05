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

"""nested files
"""
from functools import lru_cache
from os import path, listdir
import re
from tests import cached_yaml as yaml
from tests.structures import Heat

from tests.helpers import load_yaml

VERSION = "1.4.0"

"""
test nesting depth
0 -> 1 -> 2 -> too deep.
"""
MAX_DEPTH = 3


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
            if t.endswith(".yml") or t.endswith(".yaml"):
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


def get_dict_of_nested_files(yml, dirpath):
    """Return dict.
    key: resource id in yml which references a nested file.
    value: the nested file name.
    Nested files are either referenced through "type", or
    for OS::Heat::ResourceGroup, through "resource_def type".
    """
    nested_files = get_type_nested_files(yml, dirpath)
    nested_files.update(get_resourcegroup_nested_files(yml, dirpath))
    return nested_files


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


def get_nesting(yaml_files):
    """return bad, files, heat, depths
    bad - list of error messages.
    files - dict: key is filename, value is dict of nested files.
            This is the tree.
    heat - dict,: key is filename, value is Heat instance.
    depths - dict: key is filename, value is a depth tuple

    level: 0           1         2         3
    file:  template -> nested -> nested -> nested
    depth: 3           2         1         0
    """
    bad = []
    files = {}
    heat = {}
    depths = {}
    for yaml_file in yaml_files:
        dirname, basename = path.split(yaml_file)
        h = Heat(filepath=yaml_file)
        heat[basename] = h
        files[basename] = get_dict_of_nested_files(h.yml, dirname)
    for filename in files:
        depths[filename] = _get_nesting_depth_start(0, filename, files, [])
        for depth in depths[filename]:
            if depth[0] > MAX_DEPTH:
                bad.append("{} {}".format(filename, str(depth[1])))
    return bad, files, heat, depths


def _get_nesting_depth_start(depth, filename, files, context):
    depths = []
    for rid, nf in files[filename].items():
        depths.append(_get_nesting_depth(1, nf, files, context))
    return depths


def _get_nesting_depth(depth, filename, files, context):
    """Return a depth tuple (max_depth, current_context).
    `context` is the list of filenames.
    `depth` is the length of `context`.
    Finds the max_depth of all the resources of `filename`.
    current_context is the updated list of filenames
    and max_depth is its length.
    """
    max_depth = depth + 1
    current_context = context + [filename]
    if depth <= MAX_DEPTH:
        nested_filenames = files.get(filename, {})
        if nested_filenames:
            max_depth, current_context = max(
                _get_nesting_depth(depth + 1, nested_filename, files, current_context)
                for nested_filename in nested_filenames.values()
            )
    return max_depth, current_context


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
