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

import json
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path

import yaml

from preload.data import (
    AbstractPreloadDataSource,
    AbstractPreloadInstance,
    BlankPreloadInstance,
)
from preload.model import VnfModule, Vnf


def represent_ordered_dict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u"tag:yaml.org,2002:map", value)


def get_json_template(template_dir, template_name):
    template_name = template_name + ".json"
    with open(os.path.join(template_dir, template_name)) as f:
        return json.loads(f.read())


def get_or_create_template(template_dir, key, value, sequence, template_name):
    """
    Search a sequence of dicts where a given key matches value.  If
    found, then it returns that item.  If not, then it loads the
    template identified by template_name, adds it ot the sequence, and
    returns the template
    """
    for item in sequence:
        if item[key] == value:
            return item
    new_template = get_json_template(template_dir, template_name)
    sequence.append(new_template)
    return new_template


def replace(param, index=None):
    """
    Optionally used by the preload generator to wrap items in the preload
    that need to be replaced by end users
    :param param: parameter name
    :param index: optional index (int or str) of the parameter
    """
    if (param.endswith("_names") or param.endswith("_ips")) and index is not None:
        param = "{}[{}]".format(param, index)
    return "VALUE FOR: {}".format(param) if param else ""


class AbstractPreloadGenerator(ABC):
    """
    All preload generators must inherit from this class and implement the
    abstract methods.

    Preload generators are automatically discovered at runtime via a plugin
    architecture.  The system path is scanned looking for modules with the name
    preload_*, then all non-abstract classes that inherit from AbstractPreloadGenerator
    are registered as preload plugins

    Attributes:
        :param vnf:             Instance of Vnf that contains the preload data
        :param base_output_dir: Base directory to house the preloads.  All preloads
                                must be written to a subdirectory under this directory
        :param data_source:     Source data for preload population
    """

    def __init__(
        self, vnf: Vnf, base_output_dir: Path, data_source: AbstractPreloadDataSource
    ):
        self.data_source = data_source
        self.vnf = vnf
        self.base_output_dir = base_output_dir
        self.module_incomplete = False

    @classmethod
    @abstractmethod
    def format_name(cls):
        """
        String name to identify the format (ex: VN-API, GR-API)
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def output_sub_dir(cls):
        """
        String sub-directory name that will appear under ``base_output_dir``
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def supports_output_passing(cls):
        """
        Some preload methods allow automatically mapping output parameters in the
        base module to the input parameter of other modules.  This means these
        that the incremental modules do not need these base module outputs in their
        preloads.

        At this time, VNF-API does not support output parameter passing, but
        GR-API does.

        If this is true, then the generator will call Vnf#filter_output_params
        after the preload module for the base module has been created
        """
        raise NotImplementedError()

    @abstractmethod
    def generate_module(self, module: VnfModule, preload: AbstractPreloadInstance, output_dir: Path):
        """
        Create the preloads.  This method is responsible for generating the
        content of the preload and writing the file to disk.
        """
        raise NotImplementedError()

    def generate(self):
        # handle the base module first
        print("\nGenerating {} preloads".format(self.format_name()))
        if self.vnf.base_module:
            self.generate_preloads(self.vnf.base_module)
        if self.supports_output_passing():
            self.vnf.filter_base_outputs()
        for mod in self.vnf.incremental_modules:
            self.generate_preloads(mod)

    def start_module(self):
        """Initialize/reset the environment for the module"""
        self.module_incomplete = False

    def generate_preloads(self, module):
        """
        Generate a preload for the given module in all available environments
        in the ``self.preload_env``.  This will invoke the abstract
        generate_module once for each available environment **and** an
        empty environment to create a blank template.

        :param module:  module to generate for
        """
        print("\nGenerating Preloads for {}".format(module))
        print("-" * 50)
        print("... generating blank template")
        self.start_module()
        preload = BlankPreloadInstance(Path(self.base_output_dir), module.label)
        blank_preload_dir = self.make_preload_dir(preload)
        self.generate_module(module, preload, blank_preload_dir)
        self.generate_preload_env(module, preload)

        if self.data_source:
            preloads = self.data_source.get_module_preloads(module)
            for preload in preloads:
                output_dir = self.make_preload_dir(preload)
                print(
                    "... generating preload for {} to {}".format(
                        preload.module_label, output_dir
                    )
                )
                self.start_module()
                self.generate_module(module, preload, output_dir)

    def make_preload_dir(self, preload: AbstractPreloadInstance):
        preload_dir = preload.output_dir.joinpath(self.output_sub_dir())
        preload_dir.mkdir(parents=True, exist_ok=True)
        return preload_dir

    @staticmethod
    def generate_preload_env(module: VnfModule, preload: AbstractPreloadInstance):
        """
        Create a .env template suitable for completing and using for
        preload generation from env files.
        """
        yaml.add_representer(OrderedDict, represent_ordered_dict)
        output_dir = preload.output_dir.joinpath("preload_env")
        env_file = output_dir.joinpath("{}.env".format(module.label))
        defaults_file = output_dir.joinpath("defaults.yaml")
        output_dir.mkdir(parents=True, exist_ok=True)
        with env_file.open("w") as f:
            yaml.dump(module.env_template, f)
        if not defaults_file.exists():
            with defaults_file.open("w") as f:
                yaml.dump({"vnf_name": "CHANGEME"}, f)

    def normalize(self, preload_value, param_name, alt_message=None, index=None):
        preload_value = None if preload_value == "CHANGEME" else preload_value
        if preload_value:
            return preload_value
        else:
            self.module_incomplete = True
            return alt_message or replace(param_name, index)
