import importlib
import inspect
import os
import pkgutil
import shutil
from itertools import chain
from pathlib import Path
from typing import List, Type

from preload.data import AbstractPreloadDataSource
from preload.generator import AbstractPreloadGenerator
from preload.model import get_heat_templates, Vnf
from tests.helpers import get_output_dir


def create_preloads(config, exitstatus):
    """
    Create preloads in every format that can be discovered by get_generator_plugins
    """
    if config.getoption("self_test"):
        return
    print("+===================================================================+")
    print("|                      Preload Template Generation                  |")
    print("+===================================================================+")

    preload_dir = os.path.join(get_output_dir(config), "preloads")
    if os.path.exists(preload_dir):
        shutil.rmtree(preload_dir)
    plugins = PluginManager()
    available_formats = [p.format_name() for p in plugins.preload_generators]
    selected_formats = config.getoption("preload_formats") or available_formats
    preload_source = None
    if config.getoption("preload_source"):
        preload_source_path = Path(config.getoption("preload_source"))
        source_class = plugins.get_source_for_id(
            config.getoption("preload_source_type")
        )
        preload_source = source_class(preload_source_path)

    heat_templates = get_heat_templates(config)
    vnf = None
    for plugin_class in plugins.preload_generators:
        if plugin_class.format_name() not in selected_formats:
            continue
        vnf = Vnf(heat_templates)
        generator = plugin_class(vnf, preload_dir, preload_source)
        generator.generate()
    if vnf and vnf.uses_contrail:
        print(
            "\nWARNING: Preload template generation does not support Contrail\n"
            "at this time, but Contrail resources were detected. The preload \n"
            "template may be incomplete."
        )
    if exitstatus != 0:
        print(
            "\nWARNING: Heat violations detected. Preload templates may be\n"
            "incomplete or have errors."
        )


def is_implementation_of(class_, base_class):
    """
    Returns True if the class is an implementation of AbstractPreloadGenerator
    """
    return (
        inspect.isclass(class_)
        and not inspect.isabstract(class_)
        and issubclass(class_, base_class)
    )


def get_implementations_of(class_, modules):
    """
    Returns all classes that implement ``class_`` from modules
    """
    members = list(
        chain.from_iterable(
            inspect.getmembers(mod, lambda c: is_implementation_of(c, class_))
            for mod in modules
        )
    )
    return [m[1] for m in members]


class PluginManager:
    def __init__(self):
        self.preload_plugins = [
            importlib.import_module(name)
            for finder, name, ispkg in pkgutil.iter_modules()
            if name.startswith("preload_") or name == "preload"
        ]
        self.preload_generators: List[
            Type[AbstractPreloadGenerator]
        ] = get_implementations_of(AbstractPreloadGenerator, self.preload_plugins)
        self.preload_sources: List[
            Type[AbstractPreloadDataSource]
        ] = get_implementations_of(AbstractPreloadDataSource, self.preload_plugins)

    def get_source_for_id(self, identifier: str) -> Type[AbstractPreloadDataSource]:
        for source in self.preload_sources:
            if identifier == source.get_identifier():
                return source
        raise RuntimeError(
            "Unable to find preload source for identifier {}".format(identifier)
        )

    def get_source_for_name(self, name: str) -> Type[AbstractPreloadDataSource]:
        for source in self.preload_sources:
            if name == source.get_name():
                return source
        raise RuntimeError("Unable to find preload source for name {}".format(name))


PLUGIN_MGR = PluginManager()
