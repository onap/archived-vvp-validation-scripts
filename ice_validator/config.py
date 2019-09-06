import importlib
import inspect
import multiprocessing
import os
import pkgutil
import queue
from configparser import ConfigParser
from itertools import chain
from pathlib import Path
from typing import MutableMapping, Iterator, List, Optional, Dict

import appdirs
import yaml
from cached_property import cached_property

from version import VERSION
from preload.generator import AbstractPreloadGenerator
from tests.test_environment_file_parameters import ENV_PARAMETER_SPEC

PATH = os.path.dirname(os.path.realpath(__file__))
PROTOCOLS = ("http:", "https:", "file:")


def to_uri(path):
    if any(path.startswith(p) for p in PROTOCOLS):
        return path
    return Path(path).absolute().as_uri()


class UserSettings(MutableMapping):
    FILE_NAME = "UserSettings.ini"

    def __init__(self, namespace, owner):
        user_config_dir = appdirs.AppDirs(namespace, owner).user_config_dir
        if not os.path.exists(user_config_dir):
            os.makedirs(user_config_dir, exist_ok=True)
        self._settings_path = os.path.join(user_config_dir, self.FILE_NAME)
        self._config = ConfigParser()
        self._config.read(self._settings_path)

    def __getitem__(self, k):
        return self._config["DEFAULT"][k]

    def __setitem__(self, k, v) -> None:
        self._config["DEFAULT"][k] = v

    def __delitem__(self, v) -> None:
        del self._config["DEFAULT"][v]

    def __len__(self) -> int:
        return len(self._config["DEFAULT"])

    def __iter__(self) -> Iterator:
        return iter(self._config["DEFAULT"])

    def save(self):
        with open(self._settings_path, "w") as f:
            self._config.write(f)


class Config:
    """
    Configuration for the Validation GUI Application

    Attributes
    ----------
    ``log_queue``       Queue for the ``stdout`` and ``stderr` of
                        the background job
    ``log_file``        File-like object (write only!) that writes to
                        the ``log_queue``
    ``status_queue``    Job completion status of the background job is
                        posted here as a tuple of (bool, Exception).
                        The first parameter is True if the job completed
                        successfully, and False otherwise.  If the job
                        failed, then an Exception will be provided as the
                        second element.
    ``command_queue``   Used to send commands to the GUI.  Currently only
                        used to send shutdown commands in tests.
    """

    DEFAULT_FILENAME = "vvp-config.yaml"
    DEFAULT_POLLING_FREQUENCY = "1000"

    def __init__(self, config: dict = None):
        """Creates instance of application configuration.

        :param config: override default configuration if provided."""
        if config:
            self._config = config
        else:
            with open(self.DEFAULT_FILENAME, "r") as f:
                self._config = yaml.safe_load(f)
        self._user_settings = UserSettings(
            self._config["namespace"], self._config["owner"]
        )
        self._watched_variables = []
        self._validate()

    @cached_property
    def manager(self):
        return multiprocessing.Manager()

    @cached_property
    def log_queue(self):
        return self.manager.Queue()

    @cached_property
    def status_queue(self):
        return self.manager.Queue()

    @cached_property
    def log_file(self):
        return QueueWriter(self.log_queue)

    @cached_property
    def command_queue(self):
        return self.manager.Queue()

    def watch(self, *variables):
        """Traces the variables and saves their settings for the user.  The
        last settings will be used where available"""
        self._watched_variables = variables
        for var in self._watched_variables:
            var.trace_add("write", self.save_settings)

    # noinspection PyProtectedMember,PyUnusedLocal
    def save_settings(self, *args):
        """Save the value of all watched variables to user settings"""
        for var in self._watched_variables:
            self._user_settings[var._name] = str(var.get())
        self._user_settings.save()

    @property
    def app_name(self) -> str:
        """Name of the application (displayed in title bar)"""
        app_name = self._config["ui"].get("app-name", "VNF Validation Tool")
        return "{} - {}".format(app_name, VERSION)

    @property
    def category_names(self) -> List[str]:
        """List of validation profile names for display in the UI"""
        return [category["name"] for category in self._config["categories"]]

    @property
    def polling_frequency(self) -> int:
        """Returns the frequency (in ms) the UI polls the queue communicating
        with any background job"""
        return int(
            self._config["settings"].get(
                "polling-frequency", self.DEFAULT_POLLING_FREQUENCY
            )
        )

    @property
    def disclaimer_text(self) -> str:
        return self._config["ui"].get("disclaimer-text", "")

    @property
    def requirement_link_text(self) -> str:
        return self._config["ui"].get("requirement-link-text", "")

    @property
    def requirement_link_url(self) -> str:
        path = self._config["ui"].get("requirement-link-url", "")
        return to_uri(path)

    @property
    def terms(self) -> dict:
        return self._config.get("terms", {})

    @property
    def terms_link_url(self) -> Optional[str]:
        path = self.terms.get("path")
        return to_uri(path) if path else None

    @property
    def terms_link_text(self):
        return self.terms.get("popup-link-text")

    @property
    def terms_version(self) -> Optional[str]:
        return self.terms.get("version")

    @property
    def terms_popup_title(self) -> Optional[str]:
        return self.terms.get("popup-title")

    @property
    def terms_popup_message(self) -> Optional[str]:
        return self.terms.get("popup-msg-text")

    @property
    def are_terms_accepted(self) -> bool:
        version = "terms-{}".format(self.terms_version)
        return self._user_settings.get(version, "False") == "True"

    def set_terms_accepted(self):
        version = "terms-{}".format(self.terms_version)
        self._user_settings[version] = "True"
        self._user_settings.save()

    def get_description(self, category_name: str) -> str:
        """Returns the description associated with the category name"""
        return self._get_category(category_name)["description"]

    def get_category(self, category_name: str) -> str:
        """Returns the category associated with the category name"""
        return self._get_category(category_name).get("category", "")

    def get_category_value(self, category_name: str) -> str:
        """Returns the saved value for a category name"""
        return self._user_settings.get(category_name, 0)

    def _get_category(self, category_name: str) -> Dict[str, str]:
        """Returns the profile definition"""
        for category in self._config["categories"]:
            if category["name"] == category_name:
                return category
        raise RuntimeError(
            "Unexpected error: No category found in vvp-config.yaml "
            "with a name of " + category_name
        )

    @property
    def default_report_format(self):
        return self._user_settings.get("report_format", "HTML")

    @property
    def default_create_preloads(self):
        return self._user_settings.get("create_preloads", 0)

    @property
    def report_formats(self):
        return ["CSV", "Excel", "HTML"]

    @property
    def preload_formats(self):
        excluded = self._config.get("excluded-preloads", [])
        formats = (cls.format_name() for cls in get_generator_plugins())
        return [f for f in formats if f not in excluded]

    @property
    def default_preload_format(self):
        default = self._user_settings.get("preload_format")
        if default and default in self.preload_formats:
            return default
        else:
            return self.preload_formats[0]

    @staticmethod
    def get_subdir_for_preload(preload_format):
        for gen in get_generator_plugins():
            if gen.format_name() == preload_format:
                return gen.output_sub_dir()
        return ""

    @property
    def default_input_format(self):
        requested_default = self._user_settings.get("input_format") or self._config[
            "settings"
        ].get("default-input-format")
        if requested_default in self.input_formats:
            return requested_default
        else:
            return self.input_formats[0]

    @property
    def input_formats(self):
        return ["Directory (Uncompressed)", "ZIP File"]

    @property
    def default_halt_on_failure(self):
        setting = self._user_settings.get("halt_on_failure", "True")
        return setting.lower() == "true"

    @property
    def env_specs(self):
        env_specs = self._config["settings"].get("env-specs")
        specs = []
        if not env_specs:
            return [ENV_PARAMETER_SPEC]
        for mod_path, attr in (s.rsplit(".", 1) for s in env_specs):
            module = importlib.import_module(mod_path)
            specs.append(getattr(module, attr))
        return specs

    def _validate(self):
        """Ensures the config file is properly formatted"""
        categories = self._config["categories"]

        # All profiles have required keys
        expected_keys = {"name", "description"}
        for category in categories:
            actual_keys = set(category.keys())
            missing_keys = expected_keys.difference(actual_keys)
            if missing_keys:
                raise RuntimeError(
                    "Error in vvp-config.yaml file: "
                    "Required field missing in category. "
                    "Missing: {} "
                    "Categories: {}".format(",".join(missing_keys), category)
                )


class QueueWriter:
    """``stdout`` and ``stderr`` will be written to this queue by pytest, and
    pulled into the main GUI application"""

    def __init__(self, log_queue: queue.Queue):
        """Writes data to the provided queue.

        :param log_queue: the queue instance to write to.
        """
        self.queue = log_queue

    def write(self, data: str):
        """Writes ``data`` to the queue """
        self.queue.put(data)

    # noinspection PyMethodMayBeStatic
    def isatty(self) -> bool:
        """Always returns ``False``"""
        return False

    def flush(self):
        """No operation method to satisfy file-like behavior"""
        pass


def is_preload_generator(class_):
    """
    Returns True if the class is an implementation of AbstractPreloadGenerator
    """
    return (
        inspect.isclass(class_)
        and not inspect.isabstract(class_)
        and issubclass(class_, AbstractPreloadGenerator)
    )


def get_generator_plugins():
    """
    Scan the system path for modules that are preload plugins and discover
    and return the classes that implement AbstractPreloadGenerator in those
    modules
    """
    preload_plugins = (
        importlib.import_module(name)
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith("preload_")
    )
    members = chain.from_iterable(
        inspect.getmembers(mod, is_preload_generator) for mod in preload_plugins
    )
    return [m[1] for m in members]


def get_generator_plugin_names():
    return [g.format_name() for g in get_generator_plugins()]
