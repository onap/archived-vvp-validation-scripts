import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional, Mapping

from cached_property import cached_property

from preload.data import AbstractPreloadInstance, AbstractPreloadDataSource
from preload.model import VnfModule
from tests.helpers import check, first, unzip, load_yaml

SERVICE_TEMPLATE_PATTERN = re.compile(r".*service-.*?-template.yml")
RESOURCE_TEMPLATE_PATTERN = re.compile(r".*resource-(.*?)-template.yml")

ZONE_PARAMS = ("availability_zone_0", "availability_zone_1", "availability_zone_2")


def yaml_files(path):
    """
    Return files that are YAML (end with .yml or .yaml)

    :param path: Directory path object
    :return: list of paths to YAML files
    """
    return [
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in (".yml", ".yaml")
    ]


class CloudServiceArchive:
    """
    Wrapper to extract information from a CSAR file.
    """

    def __init__(self, csar_path):
        self.csar_path = Path(csar_path)
        with tempfile.TemporaryDirectory() as csar_dir:
            csar_dir = Path(csar_dir)
            unzip(self.csar_path, csar_dir)
            self._service = self._get_service_template(csar_dir)
            self._resources = self._get_vf_module_resource_templates(csar_dir)

    def get_vf_module(self, vf_module):
        """
        Retrieve the VF Module definition from the CSAR for the given heat
        module name (should not include the file extension - ex: base)

        :param vf_module: name of Heat module (no path or file extension)
        :return: The definition of the module as a dict or None if not found
        """
        if (
            vf_module.endswith(".env")
            or vf_module.endswith(".yaml")
            or vf_module.endswith(".yml")
        ):
            vf_module = os.path.splitext(vf_module)[0]
        groups = self._service.get("topology_template", {}).get("groups", {})
        for props in groups.values():
            module_label = props.get("properties", {}).get("vf_module_label", "")
            if module_label.lower() == vf_module.lower():
                return props
        return None

    def get_vf_module_model_name(self, vf_module):
        """
        Retrieves the vfModuleModelName of the module or None if vf_module is not
        found (see get_vf_module)

        :param vf_module: name of Heat module (no path or file extension)
        :return: The value if vfModuleModelName as string or None if not found
        """
        module = self.get_vf_module(vf_module)
        return module.get("metadata", {}).get("vfModuleModelName") if module else None

    @property
    def topology_template(self):
        """
        Return dict representing the topology_template node of the service
        template
        """
        return self._service.get("topology_template") or {}

    @property
    def groups(self):
        """
        Return dict representing the groups node of the service
        template
        """
        return self.topology_template.get("groups") or {}

    @property
    def vf_modules(self):
        """
        Returns mapping of group ID to VfModule present in the service template
        """
        return {
            group_id: props
            for group_id, props in self.groups.items()
            if props.get("type") == "org.openecomp.groups.VfModule"
        }

    def get_vnf_type(self, module):
        """
        Concatenation of service and VF instance name
        """
        service_name = self.service_name
        instance_name = self.get_vf_module_resource_name(module)
        if service_name and instance_name:
            return "{}/{} 0".format(service_name, instance_name)

    @property
    def vf_module_resource_names(self):
        """
        Returns the resource names for all VfModules (these can be used
        to find the resource templates as they will be part of the filename)
        """
        names = (
            module.get("metadata", {}).get("vfModuleModelName")
            for module in self.vf_modules.values()
        )
        return [name.split(".")[0] for name in names if name]

    def get_vf_module_resource_name(self, vf_module):
        """
        Retrieves the resource name of the module or None if vf_module is not
        found (see get_vf_module)

        :param vf_module: name of Heat module (no path or file extension)
        :return: The value if resource nae as string or None if not found
        """
        vf_model_name = self.get_vf_module_model_name(vf_module)
        if not vf_model_name:
            return None
        resource_name = vf_model_name.split(".")[0]
        resource = self._resources.get(resource_name, {})
        return resource.get("metadata", {}).get("name")

    @staticmethod
    def _get_definition_files(csar_dir):
        """
        Returns a list of all files in the CSAR's Definitions directory
        """
        def_dir = csar_dir / "Definitions"
        check(
            def_dir.exists(),
            "CSAR is invalid. {} does not contain a Definitions directory.".format(
                csar_dir.as_posix()
            ),
        )
        return yaml_files(def_dir)

    def _get_service_template(self, csar_dir):
        """
        Returns the service template as a dict.  Assumes there is only one.
        """
        files = map(str, self._get_definition_files(csar_dir))
        service_template = first(files, SERVICE_TEMPLATE_PATTERN.match)
        return load_yaml(service_template) if service_template else {}

    def _get_vf_module_resource_templates(self, csar_dir):
        """
        Returns a mapping of resource name to resource definition (as a dict)
        (Only loads resource templates that correspond to VF Modules
        """
        def_dir = csar_dir / "Definitions"
        mapping = (
            (name, def_dir / "resource-{}-template.yml".format(name))
            for name in self.vf_module_resource_names
        )
        return {name: load_yaml(path) for name, path in mapping if path.exists()}

    @property
    def service_name(self):
        """
        Name of the service (extracted from the service template
        """
        return self._service.get("metadata", {}).get("name")

    def __repr__(self):
        return "CSAR (path={}, name={})".format(self.csar_path.name, self.service_name)

    def __str__(self):
        return repr(self)


class PreloadEnvironment:
    def __init__(self, env_dir, parent=None):
        self.base_dir = Path(env_dir)
        self.parent = parent
        self._modules = self._load_modules()
        self._sub_env = self._load_envs()
        self._defaults = self._load_defaults()

    def _load_defaults(self):
        defaults = self.base_dir / "defaults.yaml"
        return load_yaml(defaults) if defaults.exists() else {}

    def _load_modules(self):
        files = [
            p
            for p in self.base_dir.iterdir()
            if p.is_file() and p.suffix.lower().endswith(".env")
        ]
        return {f.name.lower(): load_yaml(f).get("parameters", {}) for f in files}

    def _load_envs(self):
        env_dirs = [
            p for p in self.base_dir.iterdir() if p.is_dir() and p.name != "preloads"
        ]
        return {d.name: PreloadEnvironment(d, self) for d in env_dirs}

    @cached_property
    def csar(self):
        csar_path = first(self.base_dir.iterdir(), lambda p: p.suffix == ".csar")
        if csar_path:
            return CloudServiceArchive(csar_path)
        else:
            return self.parent.csar if self.parent else None

    @property
    def defaults(self):
        result = {}
        if self.parent:
            result.update(self.parent.defaults)
        result.update(self._defaults)
        return result

    @property
    def environments(self):
        all_envs = [self]
        for env in self._sub_env.values():
            all_envs.append(env)
            all_envs.extend(env.environments)
        return [e for e in all_envs if e.is_leaf]

    def get_module(self, name):
        name = name if name.lower().endswith(".env") else "{}.env".format(name).lower()
        if name not in self.module_names:
            return {}
        result = {}
        parent_module = self.parent.get_module(name) if self.parent else None
        module = self._modules.get(name)
        for m in (parent_module, self.defaults, module):
            if m:
                result.update(m)
        if self.csar:
            vnf_type = self.csar.get_vnf_type(name)
            if vnf_type:
                result["vnf-type"] = vnf_type
            model_name = self.csar.get_vf_module_model_name(name)
            if model_name:
                result["vf-module-model-name"] = model_name
        return result

    @property
    def module_names(self):
        parent_modules = self.parent.module_names if self.parent else set()
        result = set()
        result.update(self._modules.keys())
        result.update(parent_modules)
        return result

    @property
    def modules(self):
        return {name: self.get_module(name) for name in self.module_names}

    def get_environment(self, env_name):
        for name, env in self._sub_env.items():
            if name == env_name:
                return env
            result = env.get_environment(env_name)
            if result:
                return result
        return None

    @property
    def is_base(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self._sub_env

    @property
    def name(self):
        return self.base_dir.name

    def __repr__(self):
        return "PreloadEnvironment(name={})".format(self.name)


class EnvironmentFilePreloadInstance(AbstractPreloadInstance):
    def __init__(self, env: PreloadEnvironment, module_label: str, module_params: dict):
        self.module_params = module_params
        self._module_label = module_label
        self.env = env
        self.env_cache = {}

    @property
    def flag_incompletes(self) -> bool:
        return True

    @property
    def preload_basename(self) -> str:
        return self.module_label

    @property
    def output_dir(self) -> Path:
        return self.env.base_dir.joinpath("preloads")

    @property
    def module_label(self) -> str:
        return self._module_label

    @property
    def vf_module_name(self) -> str:
        return self.get_param("vf_module_name")

    @property
    def vnf_name(self) -> Optional[str]:
        return self.get_param("vnf_name")

    @property
    def vnf_type(self) -> Optional[str]:
        return self.get_param("vnf-type")

    @property
    def vf_module_model_name(self) -> Optional[str]:
        return self.get_param("vf-module-model-name")

    def get_availability_zone(self, index: int, param_name: str) -> Optional[str]:
        return self.get_param(param_name)

    def get_network_name(self, network_role: str, name_param: str) -> Optional[str]:
        return self.get_param(name_param)

    def get_subnet_id(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        return self.get_param(param_name)

    def get_subnet_name(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        # Not supported with env files
        return None

    def get_vm_name(self, vm_type: str, index: int, param_name: str) -> Optional[str]:
        return self.get_param(param_name, single=True)

    def get_floating_ip(
        self, vm_type: str, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        return self.get_param(param_name)

    def get_fixed_ip(
        self, vm_type: str, network_role: str, ip_version: int, index: int, param: str
    ) -> Optional[str]:
        return self.get_param(param, single=True)

    def get_vnf_parameter(self, key: str, value: Any) -> Optional[str]:
        module_value = self.get_param(key)
        return module_value or value

    def get_additional_parameters(self) -> Mapping[str, Any]:
        return {}

    def get_param(self, param_name, single=False):
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
            value = self.module_params.get(param_name)
            if isinstance(value, list):
                value = value.copy()
                value.reverse()
            self.env_cache[param_name] = value

        if value and single and isinstance(value, list):
            result = value.pop()
        else:
            result = value
        return result if result != "CHANGEME" else None


class EnvironmentFileDataSource(AbstractPreloadDataSource):
    def __init__(self, path: Path):
        super().__init__(path)
        check(path.is_dir(), f"{path} must be an existing directory")
        self.path = path
        self.env = PreloadEnvironment(path)

    @classmethod
    def get_source_type(cls) -> str:
        return "DIR"

    @classmethod
    def get_identifier(self) -> str:
        return "envfiles"

    @classmethod
    def get_name(self) -> str:
        return "Environment Files"

    def get_module_preloads(self, module: VnfModule):
        for env in self.env.environments:
            module_params = env.get_module(module.label)
            yield EnvironmentFilePreloadInstance(env, module.label, module_params)
