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
#
"""structures
"""
import collections
import inspect
import os
import re
import sys

from tests import cached_yaml as yaml
from tests.helpers import load_yaml, get_param
from .utils import nested_dict

VERSION = "4.2.0"

# key = pattern, value = regex compiled from pattern
_REGEX_CACHE = {}


def _get_regex(pattern):
    """Return a compiled version of pattern.
    Keep result in _REGEX_CACHE to avoid re-compiling.
    """
    regex = _REGEX_CACHE.get(pattern, None)
    if regex is None:
        regex = re.compile(pattern)
        _REGEX_CACHE[pattern] = regex
    return regex


class Hashabledict(dict):
    """A hashable dict.
    dicts with the same keys and whose keys have the same values
    are assigned the same hash.
    """

    def __hash__(self):
        return hash((frozenset(self), frozenset(self.values())))


class HeatProcessor(object):
    """base class for xxxx::xxxx::xxxx processors
    """

    resource_type = None  # string 'xxxx::xxxx::xxxx'
    re_rids = collections.OrderedDict()  # OrderedDict of name: regex
    # name is a string to name the regex.
    # regex parses the proper resource id format.

    @staticmethod
    def get_param_value(value, withIndex=False):
        """Return get_param value of `value`
        """
        if isinstance(value, dict) and len(value) == 1:
            v = value.get("get_param")
            if isinstance(v, list) and v:
                if withIndex and len(v) > 1:
                    idx = v[1]
                    if isinstance(idx, dict):
                        idx = idx.get("get_param", idx)
                    v = "{}{}".format(v[0], idx)
                else:
                    v = v[0]
        else:
            v = None
        return v

    @classmethod
    def get_resource_or_param_value(cls, value):
        """Return the get_resource or get_param value of `value`
        """
        if isinstance(value, dict) and len(value) == 1:
            v = value.get("get_resource") or cls.get_param_value(value)
        else:
            v = None
        return v

    @classmethod
    def get_rid_match_tuple(cls, rid):
        """find the first regex matching `rid` and return the tuple
        (name, match object) or ('', None) if no match.
        """
        rid = "" if rid is None else rid
        for name, regex in cls.re_rids.items():
            match = regex.match(rid)
            if match:
                return name, match
        return "", None

    @classmethod
    def get_rid_patterns(cls):
        """Return OrderedDict of name: friendly regex.pattern
        "friendly" means the group notation is replaced with
        braces, and the trailing "$" is removed.

        NOTE
        nested parentheses in any rid_pattern will break this parser.
        The final character is ASSUMED to be a dollar sign.
        """
        friendly_pattern = _get_regex(r"\(\?P<(.*?)>.*?\)")
        rid_patterns = collections.OrderedDict()
        for name, regex in cls.re_rids.items():
            rid_patterns[name] = friendly_pattern.sub(
                r"{\1}", regex.pattern  # replace groups with braces
            )[
                :-1
            ]  # remove trailing $
        return rid_patterns

    @classmethod
    def get_str_replace_name(cls, resource_dict):
        """Return the name modified by str_replace of `resource_dict`,
        a resource (i.e. a value in some template's resources).
        Return None, if there is no name, str_replace, its template,
        or any missing parameters.
        """
        str_replace = Heat.nested_get(
            resource_dict, "properties", "name", "str_replace"
        )
        if not str_replace:
            return None
        template = Heat.nested_get(str_replace, "template")
        if not isinstance(template, str):
            return None
        params = Heat.nested_get(str_replace, "params", default={})
        if not isinstance(params, dict):
            return None
        # WARNING
        # The user must choose non-overlapping keys for params since they
        # are replaced in the template in arbitrary order.
        name = template
        for key, value in params.items():
            param = cls.get_param_value(value, withIndex=True)
            if param is None:
                return None
            name = name.replace(key, str(param))
        return name


class CinderVolumeAttachmentProcessor(HeatProcessor):
    """ Cinder VolumeAttachment
    """

    resource_type = "OS::Cinder::VolumeAttachment"

    @classmethod
    def get_config(cls, resources):
        """Return a tuple (va_config, va_count)
        va_config - Hashabledict of Cinder Volume Attachment config
                    indexed by rid.
        va_count - dict of attachment counts indexed by rid.
        """
        va_count = collections.defaultdict(int)
        va_config = Hashabledict()
        for resource in resources.values():
            resource_type = nested_dict.get(resource, "type")
            if resource_type == cls.resource_type:
                config, rids = cls.get_volume_attachment_config(resource)
                for rid in rids:
                    va_config[rid] = config
                    va_count[rid] += 1
        return va_config, va_count

    @classmethod
    def get_volume_attachment_config(cls, resource):
        """Returns the cinder volume attachment configuration
        of `resource` as a tuple (config, rids)
        where:
        - config is a Hashabledict whose keys are the keys of the
            properties of resource, and whose values are the
            corresponding property values (nova server resource ids)
            replaced with the vm-type they reference.
        - rids is the set of nova server resource ids referenced by
            the property values.
        """
        config = Hashabledict()
        rids = set()
        for key, value in (resource.get("properties") or {}).items():
            rid = cls.get_resource_or_param_value(value)
            if rid:
                name, match = NovaServerProcessor.get_rid_match_tuple(rid)
                if name == "server":
                    vm_type = match.groupdict()["vm_type"]
                    config[key] = vm_type
                    rids.add(rid)
        return config, rids


class ContrailV2NetworkFlavorBaseProcessor(HeatProcessor):
    """ContrailV2 objects which have network_flavor
    """

    network_flavor_external = "external"
    network_flavor_internal = "internal"
    network_flavor_subint = "subinterface"

    @classmethod
    def get_network_flavor(cls, resource):
        """Return the network flavor of resource, one of
        "internal" - get_resource, or get_param contains _int_
        "subint" - get_param contains _subint_
        "external" - otherwise
        None - no parameters found to decide the flavor.

        resource.properties.virtual_network_refs should be a list.
        All the parameters in the list should have the same "flavor"
        so the flavor is determined from the first item.
        """
        network_flavor = None
        network_refs = nested_dict.get(resource, "properties", "virtual_network_refs")
        if network_refs and isinstance(network_refs, list):
            param = network_refs[0]
            if isinstance(param, dict):
                if "get_resource" in param:
                    network_flavor = cls.network_flavor_internal
                else:
                    p = param.get("get_param")
                    if isinstance(p, str):
                        if "_int_" in p or p.startswith("int_"):
                            network_flavor = cls.network_flavor_internal
                        elif "_subint_" in p:
                            network_flavor = cls.network_flavor_subint
                        else:
                            network_flavor = cls.network_flavor_external
        return network_flavor


class ContrailV2InstanceIpProcessor(ContrailV2NetworkFlavorBaseProcessor):
    """ ContrailV2 InstanceIp
    """

    resource_type = "OS::ContrailV2::InstanceIp"
    re_rids = collections.OrderedDict(
        [
            (
                "internal",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_int"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"(_v6)?"
                    r"_IP"
                    r"_(?P<index>\d+)"
                    r"$"
                ),
            ),
            (
                "subinterface",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_subint"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"(_v6)?"
                    r"_IP"
                    r"_(?P<index>\d+)"
                    r"$"
                ),
            ),
            (
                "external",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"(_v6)?"
                    r"_IP"
                    r"_(?P<index>\d+)"
                    r"$"
                ),
            ),
        ]
    )


class ContrailV2InterfaceRouteTableProcessor(HeatProcessor):
    """ ContrailV2 InterfaceRouteTable
    """

    resource_type = "OS::ContrailV2::InterfaceRouteTable"


class ContrailV2NetworkIpamProcessor(HeatProcessor):
    """ ContrailV2 NetworkIpam
    """

    resource_type = "OS::ContrailV2::NetworkIpam"


class ContrailV2PortTupleProcessor(HeatProcessor):
    """ ContrailV2 PortTuple
    """

    resource_type = "OS::ContrailV2::PortTuple"


class ContrailV2ServiceHealthCheckProcessor(HeatProcessor):
    """ ContrailV2 ServiceHealthCheck
    """

    resource_type = "OS::ContrailV2::ServiceHealthCheck"


class ContrailV2ServiceInstanceProcessor(HeatProcessor):
    """ ContrailV2 ServiceInstance
    """

    resource_type = "OS::ContrailV2::ServiceInstance"


class ContrailV2ServiceInstanceIpProcessor(HeatProcessor):
    """ ContrailV2 ServiceInstanceIp
    """

    resource_type = "OS::ContrailV2::ServiceInstanceIp"


class ContrailV2ServiceTemplateProcessor(HeatProcessor):
    """ ContrailV2 ServiceTemplate
    """

    resource_type = "OS::ContrailV2::ServiceTemplate"


class ContrailV2VirtualMachineInterfaceProcessor(ContrailV2NetworkFlavorBaseProcessor):
    """ ContrailV2 Virtual Machine Interface resource
    """

    resource_type = "OS::ContrailV2::VirtualMachineInterface"
    re_rids = collections.OrderedDict(
        [
            (
                "internal",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_int"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"$"
                ),
            ),
            (
                "subinterface",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_subint"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"$"
                ),
            ),
            (
                "external",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_(?P<network_role>.+)"
                    r"_vmi"
                    r"_(?P<vmi_index>\d+)"
                    r"$"
                ),
            ),
        ]
    )


class ContrailV2VirtualNetworkProcessor(HeatProcessor):
    """ ContrailV2 VirtualNetwork
    """

    resource_type = "OS::ContrailV2::VirtualNetwork"
    re_rids = collections.OrderedDict(
        [
            ("network", _get_regex(r"int" r"_(?P<network_role>.+)" r"_network" r"$")),
            # ("rvn", _get_regex(r"int" r"_(?P<network_role>.+)" r"_RVN" r"$")),
        ]
    )


class HeatResourceGroupProcessor(HeatProcessor):
    """ Heat ResourceGroup
    """

    resource_type = "OS::Heat::ResourceGroup"
    re_rids = collections.OrderedDict(
        [
            (
                "subint",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_subint"
                    r"_(?P<network_role>.+)"
                    r"_port_(?P<port_index>\d+)"
                    r"_subinterfaces"
                    r"$"
                ),
            )
        ]
    )


class NeutronNetProcessor(HeatProcessor):
    """ Neutron Net resource
    """

    resource_type = "OS::Neutron::Net"
    re_rids = collections.OrderedDict(
        [("network", _get_regex(r"int" r"_(?P<network_role>.+)" r"_network" r"$"))]
    )


class NeutronPortProcessor(HeatProcessor):
    """ Neutron Port resource
    """

    resource_type = "OS::Neutron::Port"
    re_rids = collections.OrderedDict(
        [
            (
                "internal",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_int"
                    r"_(?P<network_role>.+)"
                    r"_port_(?P<port_index>\d+)"
                    r"$"
                ),
            ),
            (
                "external",
                _get_regex(
                    r"(?P<vm_type>.+)"
                    r"_(?P<vm_type_index>\d+)"
                    r"_(?P<network_role>.+)"
                    r"_port_(?P<port_index>\d+)"
                    r"$"
                ),
            ),
        ]
    )

    @classmethod
    def uses_sr_iov(cls, resource):
        """Returns True/False as `resource` is/not
        An OS::Nova:Port with the property binding:vnic_type
        """
        resource_properties = nested_dict.get(resource, "properties", default={})
        if nested_dict.get(resource, "type") == cls.resource_type and resource_properties.get("binding:vnic_type", "") == "direct":
            return True

        return False


class NovaServerProcessor(HeatProcessor):
    """ Nova Server resource
    """

    resource_type = "OS::Nova::Server"
    re_rids = collections.OrderedDict(
        [
            (
                "server",
                _get_regex(r"(?P<vm_type>.+)" r"_server_(?P<vm_type_index>\d+)" r"$"),
            )
        ]
    )

    @classmethod
    def get_flavor(cls, resource):
        """Return the flavor property of `resource`
        """
        return cls.get_param_value(nested_dict.get(resource, "properties", "flavor"))

    @classmethod
    def get_image(cls, resource):
        """Return the image property of `resource`
        """
        return cls.get_param_value(nested_dict.get(resource, "properties", "image"))

    @classmethod
    def get_network(cls, resource):
        """Return the network configuration of `resource` as a
        frozenset of network-roles.
        """
        network = set()
        networks = nested_dict.get(resource, "properties", "networks")
        if isinstance(networks, list):
            for port in networks:
                value = cls.get_resource_or_param_value(nested_dict.get(port, "port"))
                name, match = NeutronPortProcessor.get_rid_match_tuple(value)
                if name:
                    network_role = match.groupdict().get("network_role")
                    if network_role:
                        network.add(network_role)
        return frozenset(network)

    @classmethod
    def get_vm_class(cls, resource):
        """Return the vm_class of `resource`, a Hashabledict (of
        hashable values) whose keys are only the required keys.
        Return empty Hashabledict if `resource` is not a NovaServer.
        """
        vm_class = Hashabledict()
        resource_type = nested_dict.get(resource, "type")
        if resource_type == cls.resource_type:
            d = dict(
                flavor=cls.get_flavor(resource),
                image=cls.get_image(resource),
                networks=cls.get_network(resource),
            )
            if all(d.values()):
                vm_class.update(d)
        return vm_class


class Heat(object):
    """A Heat template.
    filepath - absolute path to template file.
    envpath - absolute path to environmnt file.
    """

    type_bool = "boolean"
    type_boolean = "boolean"
    type_cdl = "comma_delimited_list"
    type_comma_delimited_list = "comma_delimited_list"
    type_json = "json"
    type_num = "number"
    type_number = "number"
    type_str = "string"
    type_string = "string"

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
        self.heat_processors = self.get_heat_processors()

    @property
    def contrail_resources(self):
        """This attribute is a dict of Contrail resources.
        """
        return self.get_resource_by_type(
            resource_type=ContrailV2VirtualMachineInterfaceProcessor.resource_type
        )

    def get_all_resources(self, base_dir=None, count=1):
        """
        Like ``resources``, but this returns all the resources definitions
        defined in the template, resource groups, and nested YAML files.

        A special variable will be added to all resource properties (__count__).
        This will normally be 1, but if the resource is generated by a
        ResourceGroup **and** an env file is present, then the count will be
        the value from the env file (assuming this follows standard VNF Heat
        Guidelines)
        """
        base_dir = base_dir or self.dirname
        resources = {}
        for r_id, r_data in self.resources.items():
            r_data["__count__"] = count
            resources[r_id] = r_data
            resource = Resource(r_id, r_data)
            if resource.is_nested():
                nested_count = resource.get_count(self.env)
                nested = Heat(os.path.join(base_dir, resource.get_nested_filename()))
                nested_resources = nested.get_all_resources(count=nested_count)
                resources.update(nested_resources)
        return resources

    @staticmethod
    def get_heat_processors():
        """Return a dict, key is resource_type, value is the
        HeatProcessor subclass whose resource_type is the key.
        """
        return _HEAT_PROCESSORS

    def get_resource_by_type(self, resource_type, all_resources=False):
        """Return dict of resources whose type is `resource_type`.
        key is resource_id, value is resource.
        """
        resources = self.get_all_resources() if all_resources else self.resources
        return {
            rid: resource
            for rid, resource in resources.items()
            if self.nested_get(resource, "type") == resource_type
        }

    def get_rid_match_tuple(self, rid, resource_type):
        """return get_rid_match_tuple(rid) called on the class
        corresponding to the given resource_type.
        """
        processor = self.heat_processors.get(resource_type, HeatProcessor)
        return processor.get_rid_match_tuple(rid)

    def get_vm_type(self, rid, resource=None):
        """return the vm_type
        """
        if resource is None:
            resource = self
        resource_type = self.nested_get(resource, "type")
        match = self.get_rid_match_tuple(rid, resource_type)[1]
        vm_type = match.groupdict().get("vm_type") if match else None
        return vm_type

    def load(self, filepath):
        """Load the Heat template given a filepath.
        """
        self.filepath = filepath
        self.basename = os.path.basename(self.filepath)
        self.dirname = os.path.dirname(self.filepath)
        with open(self.filepath) as fi:
            self.yml = yaml.load(fi)
        self.heat_template_version = self.yml.get("heat_template_version", None)
        self.description = self.yml.get("description", "")
        self.parameter_groups = self.yml.get("parameter_groups") or {}
        self.parameters = self.yml.get("parameters") or {}
        self.resources = self.yml.get("resources") or {}
        self.outputs = self.yml.get("outputs") or {}
        self.conditions = self.yml.get("conditions") or {}

    def load_env(self, envpath):
        """Load the Environment template given a envpath.
        """
        self.env = Env(filepath=envpath)

    @staticmethod
    def nested_get(dic, *keys, **kwargs):
        """make utils.nested_dict.get available as a class method.
        """
        return nested_dict.get(dic, *keys, **kwargs)

    @property
    def neutron_port_resources(self):
        """This attribute is a dict of Neutron Ports
        """
        return self.get_resource_by_type(
            resource_type=NeutronPortProcessor.resource_type
        )

    @property
    def nova_server_resources(self):
        """This attribute is a dict of Nova Servers
        """
        return self.get_resource_by_type(
            resource_type=NovaServerProcessor.resource_type
        )

    @staticmethod
    def part_is_in_name(part, name):
        """
        Return True if any of
        - name starts with part + '_'
        - name contains '_' + part + '_'
        - name ends with '_' + part
        False otherwise
        """
        return bool(
            re.search("(^(%(x)s)_)|(_(%(x)s)_)|(_(%(x)s)$)" % dict(x=part), name)
        )


class Env(Heat):
    """An Environment file
    """

    pass


class Resource(object):
    """A Resource
    """

    def __init__(self, resource_id=None, resource=None):
        self.resource_id = resource_id or ""
        self.resource = resource or {}
        self.properties = self.resource.get("properties", {})
        self.resource_type = self.resource.get("type", "")

    @staticmethod
    def get_index_var(resource):
        """Return the index_var for this resource.
        """
        index_var = nested_dict.get(resource, "properties", "index_var") or "index"
        return index_var

    def get_nested_filename(self):
        """Returns the filename of the nested YAML file if the
        resource is a nested YAML or ResourceDef, returns '' otherwise."""
        typ = self.resource.get("type", "")
        if typ == "OS::Heat::ResourceGroup":
            rd = nested_dict.get(self.resource, "properties", "resource_def")
            typ = rd.get("type", "") if rd else ""
        ext = os.path.splitext(typ)[1]
        ext = ext.lower()
        if ext == ".yml" or ext == ".yaml":
            return typ
        else:
            return ""

    def get_nested_properties(self):
        """
        Returns {} if not nested
        Returns resource: properties if nested
        Returns resource: properties: resource_def: properties if RG
        """
        if not bool(self.get_nested_filename()):
            return {}
        elif self.resource_type == "OS::Heat::ResourceGroup":
            return nested_dict.get(
                self.properties, "resource_def", "properties", default={}
            )
        else:
            return self.properties

    def get_count(self, env):
        if self.resource_type == "OS::Heat::ResourceGroup":
            if not env:
                return 1
            env_params = env.parameters
            count_param = get_param(self.properties["count"])
            count_value = env_params.get(count_param) if count_param else 1
            try:
                return int(count_value)
            except (ValueError, TypeError):
                print((
                    "WARNING: Invalid value for count parameter {}. Expected "
                    "an integer, but got {}. Defaulting to 1"
                ).format(count_param, count_value))
        return 1

    @property
    def depends_on(self):
        """
        Returns the list of resources this resource depends on.  Always
        returns a list.

        :return: list of all resource IDs this resource depends on.  If none,
                 then returns an empty list
        """
        parents = self.resource.get("depends_on", [])
        return parents if isinstance(parents, list) else [parents]

    def is_nested(self):
        """Returns True if the resource represents a Nested YAML resource
        using either type: {filename} or ResourceGroup -> resource_def"""
        return bool(self.get_nested_filename())

    def get_nested_yaml(self, base_dir):
        """If the resource represents a Nested YAML resource, then it
        returns the loaded YAML.  If the resource is not nested or the
        file cannot be found, then an empty dict is returned"""
        filename = self.get_nested_filename()
        if filename:
            file_path = os.path.join(base_dir, filename)
            return load_yaml(file_path) if os.path.exists(file_path) else {}
        else:
            return {}


def get_all_resources(yaml_files):
    """Return a dict, resource id: resource
    of the union of resources across all files.
    """
    resources = {}
    for heat_template in yaml_files:
        heat = Heat(filepath=heat_template)
        dirname = os.path.dirname(heat_template)
        resources.update(heat.get_all_resources(dirname))
    return resources


def _get_heat_processors():
    """Introspect this module and return a
    dict of all HeatProcessor sub-classes with a (True) resource_type.
    Key is the resource_type, value is the corrresponding class.
    """
    mod_classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    heat_processors = {
        c.resource_type: c
        for _, c in mod_classes
        if issubclass(c, HeatProcessor) and c.resource_type
    }
    return heat_processors


_HEAT_PROCESSORS = _get_heat_processors()
