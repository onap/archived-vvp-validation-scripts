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
from tests.helpers import validates, traverse
from tests.structures import Heat


class Finder:
    """
    If called sets found flag to True (used by traverse in uses_vf_module_index
    """

    def __init__(self):
        self.found = False

    def __call__(self, path, value):
        self.found = True


def uses_vf_module_index(prop_value):
    """
    Returns True if prop_value uses vf_module_index, False otherwise
    """
    finder = Finder()
    traverse(prop_value, "vf_module_index", finder)
    return finder.found


def check_vf_module_index_errors(yaml_file, resource_type, property):
    """
    Finds all resources of resource_type where the property uses vf_module_index and
    returns a set of all resource IDs that violate the condition.
    """
    resources = Heat(yaml_file).get_resource_by_type(resource_type)
    errors = set()
    for r_id, resource in resources.items():
        if (
            resource_type in ("OS::Neutron::Port", "OS::ContrailV2::InstanceIp")
            and "_int_" in r_id
        ):
            continue  # rules do not apply to internal IPs
        prop_value = resource.get("properties", {}).get(property)
        if uses_vf_module_index(prop_value):
            errors.add(r_id)
    assert not errors, (
        "The following {} resources use "
        "vf_module_index to look up the {} property, "
        "but that is not supported: {}"
    ).format(resource_type, property, ", ".join(errors))


@validates("R-55307")
def test_no_vf_module_index_server_names(yaml_file):
    check_vf_module_index_errors(yaml_file, "OS::Nova::Server", "name")


@validates("R-55307")
def test_no_vf_module_index_port_ips(yaml_file):
    check_vf_module_index_errors(yaml_file, "OS::Neutron::Port", "fixed_ips")


@validates("R-55307")
def test_no_vf_module_index_contrail_ips(yaml_file):
    check_vf_module_index_errors(
        yaml_file, "OS::ContrailV2::InstanceIp", "instance_ip_address"
    )
