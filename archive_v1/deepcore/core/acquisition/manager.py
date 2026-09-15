import importlib
import logging
from typing import Dict, Tuple, List, Type, Any
from deepcore.runtime.descriptors import ProviderDescriptor
from deepcore.core.acquisition.base import BaseConnector, BaseTranslator

logger = logging.getLogger("deepcore.acquisition.manager")

class AcquisitionManager:
    """
    Acquisition Manager. Scans and dynamically imports connector packages,
    extracting their CONNECTOR_DESCRIPTOR metadata definition, Connector implementation,
    and pure Translator implementation.
    """
    def __init__(self):
        # Maps provider_id -> (Connector class, Translator class, ProviderDescriptor instance)
        self._registry: Dict[str, Tuple[Type[BaseConnector], Type[BaseTranslator], ProviderDescriptor]] = {}

    def register_connector(self, module_name: str) -> ProviderDescriptor:
        """
        Dynamically imports a module and scans for CONNECTOR_DESCRIPTOR,
        CONNECTOR_CLASS, and TRANSLATOR_CLASS variables.
        """
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ValueError(f"Failed to register connector: Cannot import module '{module_name}'. Detail: {e}")

        # 1. Enforce Standardized CONNECTOR_DESCRIPTOR Discovery
        if not hasattr(module, "CONNECTOR_DESCRIPTOR"):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"Module must export exactly one 'CONNECTOR_DESCRIPTOR' instance of type ProviderDescriptor."
            )

        descriptor = getattr(module, "CONNECTOR_DESCRIPTOR")
        if not isinstance(descriptor, ProviderDescriptor):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"'CONNECTOR_DESCRIPTOR' must be an instance of ProviderDescriptor."
            )

        # 2. Extract Connector and Translator Classes
        if not hasattr(module, "CONNECTOR_CLASS"):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"Module must define and export 'CONNECTOR_CLASS' pointing to a BaseConnector subclass."
            )
        if not hasattr(module, "TRANSLATOR_CLASS"):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"Module must define and export 'TRANSLATOR_CLASS' pointing to a BaseTranslator subclass."
            )

        connector_class = getattr(module, "CONNECTOR_CLASS")
        translator_class = getattr(module, "TRANSLATOR_CLASS")

        if not issubclass(connector_class, BaseConnector):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"'CONNECTOR_CLASS' must inherit from BaseConnector."
            )
        if not issubclass(translator_class, BaseTranslator):
            raise ValueError(
                f"Failed to register connector in '{module_name}': "
                f"'TRANSLATOR_CLASS' must inherit from BaseTranslator."
            )

        # 3. Save to registry
        provider_id = descriptor.id
        self._registry[provider_id] = (connector_class, translator_class, descriptor)
        logger.info(f"Registered acquisition connector: {provider_id} ({descriptor.name})")

        return descriptor

    def get_connector_class(self, provider_id: str) -> Type[BaseConnector]:
        """Retrieve the BaseConnector class implementation for a registered provider."""
        if provider_id not in self._registry:
            raise KeyError(f"Connector '{provider_id}' is not registered.")
        return self._registry[provider_id][0]

    def get_translator_class(self, provider_id: str) -> Type[BaseTranslator]:
        """Retrieve the BaseTranslator class implementation for a registered provider."""
        if provider_id not in self._registry:
            raise KeyError(f"Connector '{provider_id}' is not registered.")
        return self._registry[provider_id][1]

    def get_descriptor(self, provider_id: str) -> ProviderDescriptor:
        """Retrieve the ProviderDescriptor details for a registered provider."""
        if provider_id not in self._registry:
            raise KeyError(f"Connector '{provider_id}' is not registered.")
        return self._registry[provider_id][2]

    def list_descriptors(self) -> List[ProviderDescriptor]:
        """List all currently registered ProviderDescriptors."""
        return [entry[2] for entry in self._registry.values()]
