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

from tests.parametrizers import get_nested_files
from tests.utils.network_roles import get_network_type_from_port
from .structures import Heat
from .helpers import validates, load_yaml, get_base_template_from_yaml_files


@validates("R-22688")
def test_neutron_port_internal_network_v2(yaml_files):
    base_path = get_base_template_from_yaml_files(yaml_files)
    nested_template_paths = get_nested_files(yaml_files)
    errors = []
    for yaml_file in yaml_files:
        if yaml_file == base_path or yaml_file in nested_template_paths:
            continue  # Only applies to incremental modules
        heat = Heat(filepath=yaml_file)
        internal_ports = {
            r_id: p
            for r_id, p in heat.neutron_port_resources.items()
            if get_network_type_from_port(p) == "internal"
        }
        for r_id, port in internal_ports.items():
            props = port.get("properties") or {}
            network_value = props.get("network") or {}
            if not isinstance(network_value, dict):
                continue
            if "get_param" not in network_value:
                continue  # Not connecting to network outside the template
            param = network_value.get("get_param")
            base_heat = load_yaml(base_path)
            base_outputs = base_heat.get("outputs") or {}
            if not param.endswith("_net_id"):
                errors.append(
                    (
                        "Internal network {} is attached to port {}, but the "
                        "network must be attached via UUID of the network not "
                        "the name (ex: int_{{network-role}}_net_id)."
                    ).format(param, r_id)
                )
            if param not in base_outputs:
                errors.append(
                    (
                        "Internal network {} is attached to port {}, but network "
                        "is not defined as an output in the base module ({})."
                    ).format(param, r_id, base_path)
                )

    assert not errors, " ".join(errors)
