import os
import pkgutil
import importlib
import logging

logger = logging.getLogger(__name__)

def load_engines():
    """ Dynamically discover and load all modules in the engines directory. """
    pkg_dir = os.path.dirname(__file__)
    for _, module_name, _ in pkgutil.iter_modules([pkg_dir]):
        full_module_name = f"{__name__}.{module_name}"
        try:
            importlib.import_module(full_module_name)
            logger.info(f"Loaded TTS engine module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load TTS engine module {module_name}: {e}")
