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
                template_parameters = []
                if "str_replace" in param:
                    # print(param)
                    template_parameters.extend(
                        v
                        for k, v in nested_dict.get(
                            param, "str_replace", "params", default={}
                        ).items()
                    )
                else:
                    template_parameters.append(param)

                invalid_template_parameters = []
                for template_parameter in template_parameters:
                    # Looping through each parameter to check
                    # the only case where there can be more than 1 is
                    # if using str_replace
                    msg = validate_port_parameter(
                        resource_type,
                        rid,
                        properties,
                        template_parameter,
                        resource_intext,
                        resource,
                        regx,
                        port_match,
                        exemptions_allowed,
                    )

                    if not msg:
                        # if we found a valid parameter then
                        # reset invalide_template_parameters
                        # and break out of loop
                        invalid_template_parameters = []
                        break
                    else:
                        # haven't found a valid parameter yet
                        invalid_template_parameters.append(msg)

                invalid_parameters.extend(x for x in invalid_template_parameters)

    assert not invalid_parameters, "%s" % "\n".join(invalid_parameters)


def validate_port_parameter(
    resource_type,
    rid,
    properties,
    param,
    resource_intext,
    resource,
    regx,
    port_match,
    exemptions_allowed,
):
    """
    Performs 4 validations

    1) param actually uses get_param
    2) parameter_type + network_type (internal/external) is a valid combination
    3) parameter format matches expected format from input dictionary
    4) the vm_type or network role from resource matches parameter

    If the parameter is present in the resource metadata
    and exemptions are allowed, then the validation will be skipped.
    """
    if isinstance(param, dict) and "get_param" in param:
        parameter = param.get("get_param")
    else:
        return (
            "Unexpected parameter format for {} {} property {}: {}. "
            "Please consult the heat guidelines documentation for details."
        ).format(resource_type, rid, properties, param)

    # getting parameter if the get_param uses list, and getting official
    # HEAT parameter type
    parameter_type = parameter_type_to_heat_type(parameter)
    if parameter_type == "comma_delimited_list":
        parameter = parameter[0]
    elif parameter_type != "string":
        return None

    if exemptions_allowed and parameter in get_aap_exemptions(resource):
        return None

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
        return msg

    msg = validate_parameter_format(
        regx, parameter_type, resource_intext, parameter, rid, exemptions_allowed
    )
    if msg:
        return msg

    # checking that parameter includes correct vm_type/network_role
    parameter_checks = regx.get("parameter_to_resource_comparisons", [])
    for check in parameter_checks:
        msg = mismatch_resource_and_parameter_attribute(
            check, port_match, parameter, rid
        )
        if msg:
            return msg

    return None


def validate_parameter_format(
    regx, parameter_type, resource_intext, parameter, rid, exemptions_allowed
):
    """Checks if a parameter format matches the expected format
    from input format dictionary"""
    msg = None
    regexp = regx[resource_intext][parameter_type]["machine"]
    readable_format = regx[resource_intext][parameter_type]["readable"]
    match = regexp.match(parameter)
    if not match:
        msg = (
            "{} property parameter {} does not follow {} "
            "format {} which is required by platform data model for proper "
            "assignment and inventory."
        ).format(rid, parameter, resource_intext, readable_format)
        if exemptions_allowed:
            msg = "WARNING: {} {}".format(msg, AAP_EXEMPT_CAVEAT)

    return msg


def mismatch_resource_and_parameter_attribute(check, resource_re_match, parameter, rid):
    """Compares vm_type or network_role from resource
    is the same as found in parameter"""
    resource_match = resource_re_match.group(check)
    if (
        resource_match
        and not parameter.startswith(resource_match)
        and parameter.find("_{}_".format(resource_match)) == -1
    ):
        return ("{0} {1} does not match parameter {2} {1}").format(
            rid, check, parameter
        )
