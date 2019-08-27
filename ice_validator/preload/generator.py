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

import yaml


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


def yield_by_count(sequence):
    """
    Iterates through sequence and yields each item according to its __count__
    attribute.  If an item has a __count__ of it will be returned 3 times
    before advancing to the next item in the sequence.

    :param sequence: sequence of dicts (must contain __count__)
    :returns:        generator of tuple key, value pairs
    """
    for key, value in sequence.items():
        for i in range(value["__count__"]):
            yield (key, value)


def replace(param):
    """
    Optionally used by the preload generator to wrap items in the preload
    that need to be replaced by end users
    :param param: p
    """
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
    """

    def __init__(self, vnf, base_output_dir, preload_env):
        self.preload_env = preload_env
        self.vnf = vnf
        self.current_module = None
        self.current_module_env = {}
        self.base_output_dir = base_output_dir
        self.env_cache = {}

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
    def generate_module(self, module, output_dir):
        """
        Create the preloads and write them to ``output_dir``.  This
        method is responsible for generating the content of the preload and
        writing the file to disk.
        """
        raise NotImplementedError()

    def generate(self):
        # handle the base module first
        print("\nGenerating {} preloads".format(self.format_name()))
        self.generate_environments(self.vnf.base_module)
        if self.supports_output_passing():
            self.vnf.filter_base_outputs()
        for mod in self.vnf.incremental_modules:
            self.generate_environments(mod)

    def replace(self, param_name, alt_message=None, single=False):
        value = self.get_param(param_name, single)
        if value:
            return value
        return alt_message or replace(param_name)

    def generate_environments(self, module):
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
        self.current_module = module
        self.current_module_env = {}
        self.env_cache = {}
        blank_preload_dir = self.make_preload_dir(self.base_output_dir)
        self.generate_module(module, blank_preload_dir)
        self.generate_preload_env(module, blank_preload_dir)
        if self.preload_env:
            for env in self.preload_env.environments:
                output_dir = self.make_preload_dir(env.base_dir / "preloads")
                print(
                    "... generating preload for env ({}) to {}".format(
                        env.name, output_dir
                    )
                )
                self.env_cache = {}
                self.current_module = module
                self.current_module_env = env.get_module(module.label)
                self.generate_module(module, output_dir)
        self.current_module = None
        self.current_module_env = None

    def make_preload_dir(self, base_dir):
        path = os.path.join(base_dir, self.output_sub_dir())
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def generate_preload_env(self, module, blank_preload_dir):
        """
        Create a .env template suitable for completing and using for
        preload generation from env files.
        """
        output_dir = os.path.join(blank_preload_dir, "preload_env")
        output_file = os.path.join(output_dir, "{}.env".format(module.vnf_name))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(output_file, "w") as f:
            yaml.dump(module.env_template, f)

    def get_param(self, param_name, single):
        """
        Retrieves the value for the given param if it exists. If requesting a
        single item, and the parameter is tied to a list then only one item from
        the list will be returned.  For each subsequent call with the same parameter
        it will iterate/rotate through the values in that list.  If single is False
        then the full list will be returned.

        :param param_name:  name of the parameter
        :param single:      If True returns single value from lists otherwises the full
                            list.  This has no effect on non-list values
        """
        value = self.env_cache.get(param_name)
        if not value:
            value = self.current_module_env.get(param_name)
            if isinstance(value, list):
                value.reverse()
            self.env_cache[param_name] = value
        if value and single and isinstance(value, list):
            return value.pop()
        else:
            return value
