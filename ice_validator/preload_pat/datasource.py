from pathlib import Path
from typing import Iterable, Mapping, Any, Optional

from preload.data import AbstractPreloadDataSource, AbstractPreloadInstance
from preload.model import VnfModule


class PatPreloadInstance(AbstractPreloadInstance):

    @property
    def output_dir(self) -> Path:
        pass

    @property
    def module_label(self) -> str:
        pass

    @property
    def vf_module_name(self) -> Optional[str]:
        pass

    @property
    def flag_incompletes(self) -> bool:
        pass

    @property
    def preload_basename(self) -> str:
        pass

    @property
    def vnf_name(self) -> Optional[str]:
        pass

    @property
    def vnf_type(self) -> Optional[str]:
        pass

    @property
    def vf_module_model_name(self) -> Optional[str]:
        pass

    def get_availability_zone(self, index: int, param_name: str) -> Optional[str]:
        pass

    def get_network_name(self, network_role: str, name_param: str) -> Optional[str]:
        pass

    def get_subnet_id(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        pass

    def get_subnet_name(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        pass

    def get_vm_name(self, vm_type: str, index: int, param_name: str) -> Optional[str]:
        pass

    def get_floating_ip(
        self, vm_type: str, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        pass

    def get_fixed_ip(
        self, vm_type: str, network_role: str, ip_version: int, index: int, param: str
    ) -> Optional[str]:
        pass

    def get_vnf_parameter(self, key: str, value: Any) -> Optional[Any]:
        pass

    def get_additional_parameters(self) -> Mapping[str, Any]:
        pass


class AutomationTemplateDataSource(AbstractPreloadDataSource):

    @classmethod
    def get_source_type(cls) -> str:
        return "FILE"

    @classmethod
    def get_identifier(cls) -> str:
        return "pat"

    @classmethod
    def get_name(self) -> str:
        return "vProbe Automation Template"

    def get_module_preloads(
        self, module: VnfModule
    ) -> Iterable[AbstractPreloadInstance]:
        pass
