# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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
from .network_roles import get_network_role_and_type
from tests.structures import Heat, NeutronPortProcessor
from tests.helpers import parameter_type_to_heat_type
from . import nested_dict


def check_ip_format(yaml_file, regx, port_type, resource_property, nested_property):
    """
    yaml_file: input file to check
    regx: dictionary containing the regex to use to validate parameter
    port_type: internal or external
    resource_property: OS::Neutron::Port property to check for parameter
    nested_property: resource_property will be a list of dicts, this is the key to index into
    """
    invalid_ips = []
    heat = Heat(filepath=yaml_file)
    ports = heat.get_resource_by_type("OS::Neutron::Port")
    heat_parameters = heat.parameters

    for rid, resource in ports.items():
        network_role, network_type = get_network_role_and_type(resource)
        if (
            network_type != port_type
        ):  # skipping if port type (internal/external) doesn't match
            continue

        name, port_match = NeutronPortProcessor.get_rid_match_tuple(rid)
        if not port_match:
            continue  # port resource ID not formatted correctely

        params = nested_dict.get(resource, "properties", resource_property, default={})

        for param in params:
            prop = nested_dict.get(param, nested_property)
            if (
                not prop
                or not isinstance(prop, dict)
                or "get_resource" in prop
                or "get_attr" in prop
                # or "str_replace" in prop - should str_replace be checked?
            ):
                continue  # lets only check parameters shall we?

            # checking parameter uses get_param
            parameter = nested_dict.get(prop, "get_param")
            if not parameter:
                msg = (
                    "Unexpected parameter format for OS::Neutron::Port {} property {}: {}. "
                    + "Please consult the heat guidelines documentation for details."
                ).format(rid, resource_property, prop)
                invalid_ips.append(msg)  # should this be a failure?
                continue

            # getting parameter if the get_param uses list, and getting official HEAT parameter type
            parameter_type = parameter_type_to_heat_type(parameter)
            if parameter_type == "comma_delimited_list":
                parameter = parameter[0]
            elif parameter_type != "string":
                continue

            # checking parameter format = type defined in template
            heat_parameter_type = nested_dict.get(heat_parameters, parameter, "type")
            if not heat_parameter_type or heat_parameter_type != parameter_type:
                msg = (
                    "OS::Neutron::Port {} parameter {} defined as type {} "
                    + "is being used as type {} in the heat template"
                ).format(
                    resource_property, parameter, heat_parameter_type, parameter_type
                )
                invalid_ips.append(msg)
                continue

            # if parameter type is not in regx dict, then it is not supported by automation
            regx_dict = regx[port_type].get(parameter_type)
            if not regx_dict:
                msg = (
                    "WARNING: OS::Neutron::Port {} parameter {} defined as type {} "
                    + "is not supported by platform automation. If this VNF is not able "
                    + "to adhere to this requirement, please consult the Heat Orchestration "
                    + "Template guidelines for alternative solutions. If already adhering to "
                    + "an alternative provided by the heat guidelines, please disregard this "
                    + "message."
                ).format(resource_property, parameter, parameter_type)
                invalid_ips.append(msg)
                continue

            # checking if param adheres to guidelines format
            regexp = regx[port_type][parameter_type]["machine"]
            readable_format = regx[port_type][parameter_type]["readable"]
            match = regexp.match(parameter)
            if not match:
                msg = "{} parameter {} does not follow format {}".format(
                    resource_property, parameter, readable_format
                )
                invalid_ips.append(msg)
                continue

            # checking that parameter includes correct vm_type/network_role
            parameter_checks = regx.get("parameter_to_resource_comparisons", [])
            for check in parameter_checks:
                resource_match = port_match.group(check)
                if (
                    resource_match
                    and not parameter.startswith(resource_match)
                    and parameter.find("_{}_".format(resource_match)) == -1
                ):
                    msg = (
                        "OS::Neutron::Port {0} property {1} parameter "
                        + "{2} {3} does match resource {3} {4}"
                    ).format(rid, resource_property, parameter, check, resource_match)
                    invalid_ips.append(msg)
                    continue

    assert not invalid_ips, "%s" % "\n".join(invalid_ips)


def get_list_of_ports_attached_to_nova_server(nova_server):
    networks_list = nova_server.get("properties", {}).get("networks")

    port_ids = []
    if networks_list:
        for network in networks_list:
            network_prop = network.get("port")
            if network_prop:
                pid = network_prop.get("get_param")
                if not pid:
                    pid = network_prop.get("get_resource")
                port_ids.append(pid)

    return port_ids
