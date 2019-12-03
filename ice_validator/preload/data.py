from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Any, Optional, Mapping

from preload.model import VnfModule


class AbstractPreloadInstance(ABC):
    """
    Represents the data source for a single instance of a preload for
    any format.  The implementation of AbstractPreloadGenerator will
    call the methods of this class to retrieve the necessary data
    to populate the preload.  If a data element is not available,
    then simply return ``None`` and a suitable placeholder will be
    placed in the preload.
    """

    @property
    @abstractmethod
    def output_dir(self) -> Path:
        """
        Base output directory where the preload will be generated.  Please
        note, that the generator may create nested directories under this
        directory for the preload.

        :return: Path to the desired output directory.  This directory
                 and its parents will be created by the generator if
                 it is not already present.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def module_label(self) -> str:
        """
        Identifier of the module.  This must match the base name of the
        heat module (ex: if the Heat file name is base.yaml, then the label
        is 'base'.

        :return: string name of the module
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def vf_module_name(self) -> Optional[str]:
        """
        :return: module name to populate in the preload if available
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def flag_incompletes(self) -> bool:
        """
        If True, then the generator will modify the file name of any
        generated preload to end with _incomplete.<ext> if any preload
        value was not satisfied by the data source.  If False, then
        the file name will be the same regardless of the completeness
        of the preload.

        :return: True if file names should denote preload incompleteness
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def preload_basename(self) -> str:
        """
        Base name of the preload that will be used by the generator to create
        the file name.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def vnf_name(self) -> Optional[str]:
        """
        :return: the VNF name to populate in the prelad if available
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def vnf_type(self) -> Optional[str]:
        """
        The VNF Type must be match the values in SDC.  It is a concatenation
        of <Service Instance Name>/<Resource Instance Name>.

        :return: VNF Type to populate in the preload if available
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def vf_module_model_name(self) -> Optional[str]:
        """
        :return: Module model name if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_availability_zone(self, index: int, param_name: str) -> Optional[str]:
        """
        Retrieve the value for the availability zone at requested zero-based
        index (i.e. 0, 1, 2, etc.)

        :param index:       index of availability zone (0, 1, etc.)
        :param param_name:  Name of the parameter from Heat
        :return:            value for the AZ if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_network_name(self, network_role: str, name_param: str) -> Optional[str]:
        """
        Retrieve the OpenStack name of the network for the given network role.

        :param network_role:    Network role from Heat template
        :param name_param:      Network name parameter from Heat
        :return:                Name of the network if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_subnet_id(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        """
        Retrieve the subnet's UUID for the given network and IP version (4 or 6).

        :param network_role:    Network role from Heat template
        :param ip_version:      IP Version (4 or 6)
        :param param_name:      Parameter name from Heat
        :return:                UUID of the subnet if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_subnet_name(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        """
        Retrieve the OpenStack Subnet name for the given network role and IP version

        :param network_role:    Network role from Heat template
        :param ip_version:      IP Version (4 or 6)
        :param param_name:      Parameter name from Heat
        :return:                Name of the subnet if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_vm_name(self, vm_type: str, index: int, param_name: str) -> Optional[str]:
        """
        Retrieve the vm name for the given VM type and index.

        :param vm_type:         VM Type from Heat template
        :param index:           Zero-based index of the VM for the vm-type
        :param param_name:      Parameter name from Heat
        :return:                VM Name if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_floating_ip(
        self, vm_type: str, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        """
        Retreive the floating IP for the VM and Port identified by VM Type,
        Network Role, and IP Version.

        :param vm_type:         VM Type from Heat template
        :param network_role:    Network Role from Heat template
        :param ip_version:      IP Version (4 or 6)
        :param param_name:      Parameter name from Heat
        :return: floating IP address if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_fixed_ip(
        self, vm_type: str, network_role: str, ip_version: int, index: int, param: str
    ) -> Optional[str]:
        """
        Retreive the fixed IP for the VM and Port identified by VM Type,
        Network Role, IP Version, and index.

        :param vm_type:         VM Type from Heat template
        :param network_role:    Network Role from Heat template
        :param ip_version:      IP Version (4 or 6)
        :param index:           zero-based index for the IP for the given
                                VM Type, Network Role, IP Version combo
        :param param_name:      Parameter name from Heat
        :return: floating IP address if available
        """
        raise NotImplementedError()

    @abstractmethod
    def get_vnf_parameter(self, key: str, value: Any) -> Optional[Any]:
        """
        Retrieve the value for the given key.  These will be placed in the
        tag-values/vnf parameters in the preload.  If a value was specified in
        the environment packaged in the Heat for for the VNF module, then
        that value will be  passed in ``value``.  This class can return
        the value or ``None`` if it does not have a value for the given key.

        :param key:     parameter name from Heat
        :param value:   Value from Heat env file if it was assigned there;
                        None otherwise
        :return:        Returns the value for the object.  This should
                        be a str, dict, or list.  The generator will
                        format it properly based on the selected output format
        """
        raise NotImplementedError()

    @abstractmethod
    def get_additional_parameters(self) -> Mapping[str, Any]:
        """
        Return any additional parameters that should be added to the VNF parameters.

        This can be useful if you want to duplicate paramters in tag values that are
        also in the other sections (ex: VM names).

        :return: dict of str to object mappings that the generator must add to
                 the vnf_parameters/tag values
        """
        raise NotImplementedError()


class AbstractPreloadDataSource(ABC):
    """
    Represents a data source for a VNF preload data.  Implementations of this
    class can be dynamically discovered if they are in a preload plugin module.
    A module is considered a preload plugin module if it starts with
    prelaod_ and is available as a top level module on Python's sys.path.

    The ``get_module_preloads`` will be invoked for each module in
    the VNF.  An instance of AbstractPreloadInstance must be returned for
    each instance of the preload module that is to be created.

    Parameters:
        :param path:    The path to the configuration source selected
                        in either the VVP GUI or command-line.  This
                        may be a file or directory depending upon
                        the source_type defined by this data source
    """

    def __init__(self, path: Path):
        self.path = path

    @classmethod
    @abstractmethod
    def get_source_type(cls) -> str:
        """
        If 'FILE' returned, then the config source will be a specific
        file; If 'DIR', then the config source will be a directory
        :return:
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_identifier(cls) -> str:
        """
        Identifier for the given data source. This is the value that
        can be passed via --preload-source-type.

        :return: short identifier for this data source type
        """

    @classmethod
    @abstractmethod
    def get_name(self) -> str:
        """
        Human readable name to describe the preload data source. It is
        recommended not to exceed 50 characters.

        :return: human readable name of the preload data source (ex: Environment Files)
        """
        raise NotImplementedError()

    @abstractmethod
    def get_module_preloads(
        self, module: VnfModule
    ) -> Iterable[AbstractPreloadInstance]:
        """
        For the  requested module, return an instance of AbstractPreloadInstance
        for every preload module you wish to be created.

        :param module:  Module of the VNF
        :return:        iterable of preloads to create for the given module
        """
        raise NotImplementedError()


class BlankPreloadInstance(AbstractPreloadInstance):
    """
    Used to create blank preload templates.  VVP will always create
    a template of a preload in the requested format with no data provided.
    """

    def __init__(self, output_dir: Path, module_name: str):
        self._output_dir = output_dir
        self._module_name = module_name

    @property
    def flag_incompletes(self) -> bool:
        return False

    @property
    def preload_basename(self) -> str:
        return self._module_name

    @property
    def vf_module_name(self) -> Optional[str]:
        return None

    def get_vm_name(self, vm_type: str, index: int, param_name: str) -> Optional[str]:
        return None

    def get_availability_zone(self, index: int, param_name: str) -> Optional[str]:
        return None

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    @property
    def module_label(self) -> str:
        return self._module_name

    @property
    def vnf_name(self) -> Optional[str]:
        return None

    @property
    def vnf_type(self) -> Optional[str]:
        return None

    @property
    def vf_module_model_name(self) -> Optional[str]:
        return None

    def get_network_name(self, network_role: str, name_param: str) -> Optional[str]:
        return None

    def get_subnet_id(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        return None

    def get_subnet_name(
        self, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        return None

    def get_floating_ip(
        self, vm_type: str, network_role: str, ip_version: int, param_name: str
    ) -> Optional[str]:
        return None

    def get_fixed_ip(
        self, vm_type: str, network_role: str, ip_version: int, index: int, param: str
    ) -> Optional[str]:
        return None

    def get_vnf_parameter(self, key: str, value: Any) -> Optional[Any]:
        return None

    def get_additional_parameters(self) -> Mapping[str, Any]:
        return {}
