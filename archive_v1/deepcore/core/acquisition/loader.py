import pkgutil
import importlib
import logging
from typing import List, Optional
from deepcore.runtime.descriptors import CapabilityRegistry, ProviderDescriptor
from deepcore.core.acquisition.manager import AcquisitionManager

logger = logging.getLogger("deepcore.acquisition.loader")


class ConnectorLoader:
    """
    Dynamically discovers and loads connector modules from deepcore.connectors,
    extracting their ProviderDescriptor metadata definitions and registering them
    with both the CapabilityRegistry and AcquisitionManager.
    """
    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        acquisition_manager: Optional[AcquisitionManager] = None,
        package_name: str = "deepcore.connectors"
    ):
        self.capability_registry = capability_registry
        self.acquisition_manager = acquisition_manager or AcquisitionManager()
        self.package_name = package_name

    def discover_and_register(self) -> List[ProviderDescriptor]:
        """
        Scans the connectors package directory, imports each module/subpackage,
        and registers its ProviderDescriptor into CapabilityRegistry and AcquisitionManager.
        """
        registered_descriptors: List[ProviderDescriptor] = []
        try:
            package = importlib.import_module(self.package_name)
        except ImportError as e:
            logger.warning(f"ConnectorLoader: Package '{self.package_name}' could not be imported: {e}")
            return registered_descriptors

        package_path = getattr(package, "__path__", None)
        if not package_path:
            return registered_descriptors

        for _, modname, ispkg in pkgutil.iter_modules(package_path):
            full_mod_name = f"{self.package_name}.{modname}"
            descriptor_mod_name = f"{full_mod_name}.descriptor" if ispkg else full_mod_name
            
            try:
                mod = importlib.import_module(descriptor_mod_name)
            except ImportError:
                try:
                    mod = importlib.import_module(full_mod_name)
                except ImportError as err:
                    logger.debug(f"ConnectorLoader: Could not import '{full_mod_name}': {err}")
                    continue

            descriptor = getattr(mod, "CONNECTOR_DESCRIPTOR", None)
            if descriptor and isinstance(descriptor, ProviderDescriptor):
                try:
                    self.capability_registry.register(descriptor)
                except Exception as e:
                    logger.debug(f"Descriptor '{descriptor.id}' already registered in registry: {e}")

                # If the loaded module was descriptor.py, look up CONNECTOR_CLASS on the package module instead
                target_mod = mod
                if ispkg and (not hasattr(target_mod, "CONNECTOR_CLASS") or not hasattr(target_mod, "TRANSLATOR_CLASS")):
                    try:
                        target_mod = importlib.import_module(full_mod_name)
                    except ImportError:
                        pass

                if hasattr(target_mod, "CONNECTOR_CLASS") and hasattr(target_mod, "TRANSLATOR_CLASS"):
                    try:
                        self.acquisition_manager.register_connector(full_mod_name)
                    except Exception as e:
                        logger.warning(f"AcquisitionManager registration deferred for '{full_mod_name}': {e}")

                registered_descriptors.append(descriptor)
                logger.info(f"ConnectorLoader: Registered capability provider '{descriptor.id}' ({descriptor.name})")

        return registered_descriptors
