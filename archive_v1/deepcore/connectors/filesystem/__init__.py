from deepcore.connectors.filesystem.descriptor import CONNECTOR_DESCRIPTOR
from deepcore.connectors.filesystem.connector import FilesystemConnector
from deepcore.connectors.filesystem.translator import MarkdownTranslator

CONNECTOR_CLASS = FilesystemConnector
TRANSLATOR_CLASS = MarkdownTranslator
