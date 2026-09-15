import pytest
from deepcore.core.acquisition.base import (
    BaseConnector,
    ConnectorOperation,
    ExecutionContext,
    ExecutionRequest,
    ExecutionResponse,
    ConnectorCapabilities,
    HealthStatus,
    SyncContext,
)
from deepcore.connectors.filesystem.connector import FilesystemConnector
from deepcore.connectors.calendar.connector import CalendarConnector
from deepcore.connectors.spotlight.connector import SpotlightConnector


class MinimalTestConnector(BaseConnector):
    """Concrete minimal connector to test default BaseConnector live implementations."""
    def authenticate(self, credentials):
        return HealthStatus(state="HEALTHY")

    def discover(self, ctx):
        yield {}

    def sync(self, ctx):
        yield {}

    def watch(self, ctx):
        yield {}

    def health(self, ctx):
        return HealthStatus(state="HEALTHY")


def test_connector_operation_enum():
    assert ConnectorOperation.SEARCH.value == "search"
    assert ConnectorOperation.READ.value == "read"
    assert ConnectorOperation.LIST.value == "list"
    assert ConnectorOperation.QUERY.value == "query"
    assert ConnectorOperation.ACTION.value == "action"


def test_execution_context_defaults():
    ctx = ExecutionContext()
    assert ctx.config == {}
    assert ctx.credentials == {}
    assert ctx.workspace_id is None
    assert ctx.source_id is None


def test_execution_request_and_response_validation():
    ctx = ExecutionContext(config={"path": "/tmp"})
    req = ExecutionRequest(
        operation=ConnectorOperation.READ,
        parameters={"path": "/tmp/test.txt"},
        context=ctx,
        limits={"max_results": 10}
    )
    assert req.operation == ConnectorOperation.READ
    assert req.parameters["path"] == "/tmp/test.txt"
    assert req.limits["max_results"] == 10

    resp = ExecutionResponse(
        results=[{"id": 1, "title": "test"}],
        metadata={"total": 1},
        diagnostics={"latency_ms": 12.5}
    )
    assert len(resp.results) == 1
    assert resp.metadata["total"] == 1
    assert resp.diagnostics["latency_ms"] == 12.5


def test_connector_capabilities_defaults():
    caps = ConnectorCapabilities(
        supported_operations=[ConnectorOperation.READ, ConnectorOperation.LIST],
        requires_configuration=True,
        supports_pagination=True
    )
    assert ConnectorOperation.READ in caps.supported_operations
    assert ConnectorOperation.LIST in caps.supported_operations
    assert caps.requires_configuration is True
    assert caps.supports_pagination is True
    assert caps.supports_streaming is False


def test_base_connector_default_live_methods():
    connector = MinimalTestConnector()
    
    # 1. capabilities() default
    caps = connector.capabilities()
    assert isinstance(caps, ConnectorCapabilities)
    assert caps.supported_operations == []

    # 2. check_health() default
    health = connector.check_health()
    assert isinstance(health, HealthStatus)
    assert health.state == "HEALTHY"

    # 3. execute() default raises NotImplementedError
    req = ExecutionRequest(operation=ConnectorOperation.SEARCH)
    with pytest.raises(NotImplementedError) as exc_info:
        connector.execute(req)
    assert "Live operation 'search' is not implemented" in str(exc_info.value)


def test_existing_connectors_backward_compatibility():
    """Verify existing V1 connectors instantiate and possess default live methods without modifications."""
    fs_conn = FilesystemConnector()
    cal_conn = CalendarConnector()
    spot_conn = SpotlightConnector()

    for conn in (fs_conn, cal_conn, spot_conn):
        assert isinstance(conn.capabilities(), ConnectorCapabilities)
        assert conn.check_health().state == "HEALTHY"
        with pytest.raises(NotImplementedError):
            conn.execute(ExecutionRequest(operation=ConnectorOperation.ACTION))
