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

"""
forbidden resources
"""

from .structures import Heat
from .helpers import validates


VERSION = "1.1.1"


def run_test(heat_template, forbidden):
    """run
    """
    heat = Heat(filepath=heat_template)
    bad = set()
    for rid, resource in heat.resources.items():
        if heat.nested_get(resource, "type") == forbidden:
            bad.add(rid)
    assert not bad, 'resource(s) with forbidden type "%s" %s' % (forbidden, list(bad))


# pylint: disable=invalid-name


@validates("R-05257")
def test_neutron_floating_ip_resource_type(heat_template):
    """
    A VNF's Heat Orchestration Template's **MUST NOT**
    contain the Resource ``OS::Neutron::FloatingIP``.
    """
    run_test(heat_template, "OS::Neutron::FloatingIP")


@validates("R-76449")
def test_neutron_floating_ip_association_resource_type(heat_template):
    """
    A VNF's Heat Orchestration Template's **MUST NOT**
    contain the Resource ``OS::Neutron::FloatingIPAssociation``.
    """
    run_test(heat_template, "OS::Neutron::FloatingIPAssociation")
