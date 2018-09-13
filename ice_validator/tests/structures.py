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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

'''structures
'''

import os

from tests import cached_yaml as yaml

from .utils import nested_dict

VERSION = '1.4.0'


class Heat(object):
    """A Heat template.
    filepath - absolute path to template file.
    envpath - absolute path to environmnt file.
    """
    def __init__(self, filepath=None, envpath=None):
        self.filepath = None
        self.basename = None
        self.dirname = None
        self.yml = None
        self.heat_template_version = None
        self.description = None
        self.parameter_groups = None
        self.parameters = None
        self.resources = None
        self.outputs = None
        self.conditions = None
        if filepath:
            self.load(filepath)
        self.env = None
        if envpath:
            self.load_env(envpath)

    def load(self, filepath):
        """Load the Heat template given a filepath.
        """
        self.filepath = filepath
        self.basename = os.path.basename(self.filepath)
        self.dirname = os.path.dirname(self.filepath)
        with open(self.filepath) as fi:
            self.yml = yaml.load(fi)
        self.heat_template_version = self.yml.get('heat_template_version', None)
        self.description = self.yml.get('description', '')
        self.parameter_groups = self.yml.get('parameter_groups', {})
        self.parameters = self.yml.get('parameters', {})
        self.resources = self.yml.get('resources', {})
        self.outputs = self.yml.get('outputs', {})
        self.conditions = self.yml.get('conditions', {})

    def load_env(self, envpath):
        """Load the Environment template given a envpath.
        """
        self.env = Env(filepath=envpath)

    @staticmethod
    def nested_get(dic, *keys):
        """make utils.nested_dict.get available as a class method.
        """
        return nested_dict.get(dic, *keys)


class Env(Heat):
    """An Environment file
    """
    pass


class Resource(object):
    """A Resource
    """
    def __init__(self, resource_id=None, resource=None):
        self.resource_id = resource_id or ''
        self.resource = resource or {}

    @staticmethod
    def get_index_var(resource):
        """Return the index_var for this resource.
        """
        index_var = nested_dict.get(resource,
                                    'properties',
                                    'index_var') or 'index'
        return index_var

