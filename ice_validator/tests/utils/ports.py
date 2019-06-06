# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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
from tests.structures import Heat
from tests.helpers import parameter_type_to_heat_type, prop_iterator
from . import nested_dict


AAP_EXEMPT_CAVEAT = (
    "If this VNF is not able to adhere to this requirement, please consult the Heat "
    "Orchestration Template guidelines for more information. If you are knowingly "
    "violating this requirement after reading the guidelines, then add the parameter "
    "to the aap_exempt list under this resources metadata to suppress this warning."
)


def get_aap_exemptions(resource_props):
    """
    Gets the list of parameters that the Heat author has exempted from following
    the naming conventions associated with AAP.

    :param resource_props: dict of properties under the resource ID
    :return: list of all parameters to exempt or an empty list
    """
    metadata = resource_props.get("metadata") or {}
    return metadata.get("aap_exempt") or []


def check_parameter_format(
    yaml_file, regx, intext, resource_processor, *properties, exemptions_allowed=False
):
    """
    yaml_file: input file to check
    regx: dictionary containing the regex to use to validate parameter
    intext: internal or external
    resource_processor: resource type specific helper, defined in structures.py
    properties: arg list of property that is being checked
    exemptions_allowed: If True, then parameters in the aap_exempt list are allowed to
                        not follow the rules
    """

    invalid_parameters = []
    heat = Heat(filepath=yaml_file)
    resource_type = resource_processor.resource_type
    resources = heat.get_resource_by_type(resource_type)
    heat_parameters = heat.parameters
    for rid, resource in resources.items():
        resource_intext, port_match = resource_processor.get_rid_match_tuple(rid)
        if not port_match:
            continue  # port resource ID not formatted correctely

        if (
            resource_intext != intext
        ):  # skipping if type (internal/external) doesn't match
            continue

        for param in prop_iterator(resource, *properties):
            if (
                param
                and isinstance(param, dict)
                and "get_resource" not in param
                and "get_attr" not in param
            ):
                # checking parameter uses get_param
                parameter = param.get("get_param")
                if not parameter:
                    msg = (
                        "Unexpected parameter format for {} {} property {}: {}. "
                        "Please consult the heat guidelines documentation for details."
                    ).format(resource_type, rid, properties, param)
                    invalid_parameters.append(msg)  # should this be a failure?
                    continue

                # getting parameter if the get_param uses list, and getting official
                # HEAT parameter type
                parameter_type = parameter_type_to_heat_type(parameter)
                if parameter_type == "comma_delimited_list":
                    parameter = parameter[0]
                elif parameter_type != "string":
                    continue

                # checking parameter format = parameter type defined in parameters
                # section
                heat_parameter_type = nested_dict.get(
                    heat_parameters, parameter, "type"
                )
                if not heat_parameter_type or heat_parameter_type != parameter_type:
                    msg = (
                        "{} {} parameter {} defined as type {} "
                        + "is being used as type {} in the heat template"
                    ).format(
                        resource_type,
                        properties,
                        parameter,
                        heat_parameter_type,
                        parameter_type,
                    )
                    invalid_parameters.append(msg)  # should this actually be an error?
                    continue

                if exemptions_allowed and parameter in get_aap_exemptions(resource):
                    continue

                # if parameter type is not in regx dict, then it is not supported
                # by automation
                regx_dict = regx[resource_intext].get(parameter_type)
                if not regx_dict:
                    msg = (
                        "{} {} {} parameter {} defined as type {} "
                        "which is required by platform data model for proper "
                        "assignment and inventory."
                    ).format(resource_type, rid, properties, parameter, parameter_type)
                    if exemptions_allowed:
                        msg = "WARNING: {} {}".format(msg, AAP_EXEMPT_CAVEAT)
                    invalid_parameters.append(msg)
                    continue

                # checking if param adheres to guidelines format
                regexp = regx[resource_intext][parameter_type]["machine"]
                readable_format = regx[resource_intext][parameter_type]["readable"]
                match = regexp.match(parameter)
                if not match:
                    msg = (
                        "{} {} property {} parameter {} does not follow {} "
                        "format {} which is required by platform data model for proper "
                        "assignment and inventory."
                    ).format(
                        resource_type,
                        rid,
                        properties,
                        parameter,
                        resource_intext,
                        readable_format,
                    )
                    if exemptions_allowed:
                        msg = "WARNING: {} {}".format(msg, AAP_EXEMPT_CAVEAT)
                    invalid_parameters.append(msg)
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
                            "{0} {1} property {2} parameter "
                            "{3} {4} does match resource {4} {5}"
                        ).format(
                            resource_type,
                            rid,
                            properties,
                            parameter,
                            check,
                            resource_match,
                        )
                        invalid_parameters.append(msg)
                        continue

    assert not invalid_parameters, "%s" % "\n".join(invalid_parameters)


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
