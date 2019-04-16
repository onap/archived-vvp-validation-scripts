import os
import re

import pytest

from tests.helpers import validates, get_base_template_from_yaml_files
from tests.parametrizers import get_nested_files
from tests.structures import Heat

INTERNAL_UUID_PATTERN = re.compile(r"^int_(?P<network_role>.+?)_net_id$")
INTERNAL_NAME_PATTERN = re.compile(r"^int_(?P<network_role>.+?)_net_name$")
INTERNAL_PORT = re.compile(r"^(?P<vm_type>.+)_(?P<vm_type_index>\d+)_int_"
                           r"(?P<network_role>.+)_port_(?P<port_index>\d+)$")

EXTERNAL_PORT = re.compile(r"^(?P<vm_type>.+)_(?P<vm_type_index>\d+)_(?!int_)"
                           r"(?P<network_role>.+)_port_(?P<port_index>\d+)$")

EXTERNAL_UUID_PATTERN = re.compile(r"^(?!int_)(?P<network_role>.+?)_net_id$")
EXTERNAL_NAME_PATTERN = re.compile(r"^(?!int_)(?P<network_role>.+?)_net_name$")

INTERNAL_NETWORK_PATTERN = re.compile(r"^int_(?P<network_role>.+?)"
                                      r"_(network|RVN)$")


def is_incremental_module(yaml_file, base_path, nested_paths):
    return yaml_file != base_path and yaml_file not in nested_paths


def get_param(prop_val):
    if not isinstance(prop_val, dict):
        return None
    param = prop_val.get("get_param")
    return param if isinstance(param, str) else None


@validates("R-86182", "R-22688")
def test_internal_network_parameters(yaml_files):
    base_path = get_base_template_from_yaml_files(yaml_files)
    if not base_path:
        pytest.skip("No base module found")
    base_heat = Heat(filepath=base_path)
    nested_paths = get_nested_files(yaml_files)
    incremental_modules = [f for f in yaml_files
                           if is_incremental_module(f, base_path, nested_paths)]
    errors = []
    for module in incremental_modules:
        heat = Heat(filepath=module)
        for rid, port in heat.neutron_port_resources.items():
            rid_match = INTERNAL_PORT.match(rid)
            if not rid_match:
                continue

            network = (port.get("properties") or {}).get("network") or {}
            if isinstance(network, dict) and (
                    "get_resource" in network or "get_attr" in network):
                continue

            param = get_param(network)
            if not param:
                errors.append((
                    "The internal port ({}) must either connect to a network "
                    "in the base module using get_param or to a network "
                    "created in this module ({})"
                ).format(rid, os.path.split(module)[1]))
                continue

            param_match = (
                INTERNAL_UUID_PATTERN.match(param)
                or INTERNAL_NAME_PATTERN.match(param)
            )
            if not param_match:
                errors.append((
                    "The internal port ({}) network parameter ({}) does not "
                    "match one of the required naming conventions of "
                    "int_{{network-role}}_net_id or "
                    "int_{{network-role}}_net_name "
                    "for connecting to an internal network. "
                    "If this is not an internal port, then change the resource "
                    "ID to adhere to the external port naming convention."
                ).format(rid, param))
                continue

            if param not in base_heat.yml.get("outputs", {}):
                base_module = os.path.split(base_path)[1]
                errors.append((
                    "The internal network parameter ({}) attached to port ({}) "
                    "must be defined in the output section of the base module ({})."
                ).format(param, rid, base_module))
                continue

            param_network_role = param_match.groupdict().get("network_role")
            rid_network_role = rid_match.groupdict().get("network_role")
            if param_network_role.lower() != rid_network_role.lower():
                errors.append((
                    "The network role ({}) extracted from the resource ID ({}) "
                    "does not match network role ({}) extracted from the "
                    "network parameter ({})"
                ).format(rid_network_role, rid, param_network_role, param))

            resources = base_heat.get_all_resources(os.path.split(base_path)[0])
            networks = {rid: resource for rid, resource in resources.items()
                        if resource.get("type")
                        in {"OS::Neutron::Net",
                            "OS::ContrailV2::VirtualNetwork"}}
            matches = (INTERNAL_NETWORK_PATTERN.match(n) for n in networks)
            roles = {m.groupdict()["network_role"].lower() for m in matches if m}
            if param_network_role.lower() not in roles:
                errors.append((
                    "No internal network with a network role of {} was "
                    "found in the base modules networks: {}"
                ).format(param_network_role, ", ".join(networks)))

    assert not errors, ". ".join(errors)


@validates("R-62983")
def test_external_network_parameter(heat_template):
    heat = Heat(filepath=heat_template)
    errors = []
    for rid, port in heat.neutron_port_resources.items():
        rid_match = EXTERNAL_PORT.match(rid)
        if not rid_match:
            continue   # only test external ports
        network = (port.get("properties") or {}).get("network") or {}
        if not isinstance(network, dict) or "get_param" not in network:
            errors.append((
                "The external port ({}) must assign the network property "
                "using get_param.  If this port is for an internal network, "
                "then change the resource ID format to the external format."
            ).format(rid))
            continue
        param = get_param(network)
        if not param:
            errors.append((
                "The get_param function on the network property of port ({}) "
                "must only take a single, string parameter."
            ).format(rid))
            continue

        param_match = (
            EXTERNAL_NAME_PATTERN.match(param)
            or EXTERNAL_UUID_PATTERN.match(param)
        )
        if not param_match:
            errors.append((
                "The network parameter ({}) on port ({}) does not match one of "
                "{{network-role}}_net_id or {{network-role}}_net_name."
            ).format(param, rid))
            continue
        rid_network_role = rid_match.groupdict()["network_role"]
        param_network_role = param_match.groupdict()["network_role"]
        if rid_network_role.lower() != param_network_role.lower():
            errors.append((
                "The network role ({}) extracted from the resource ID ({}) "
                "does not match network role ({}) extracted from the "
                "network parameter ({})"
            ).format(rid_network_role, rid, param_network_role, param))

    assert not errors, ". ".join(errors)
