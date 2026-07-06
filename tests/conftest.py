import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Override database configuration env var to use a test-specific file
os.environ["DEEPCORE_DB_PATH"] = "test_deepcore.db"

from deepcore.storage.sqlite.db import Base, get_db
from deepcore.api.main import app

TEST_DATABASE_URL = "sqlite:///test_deepcore.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Ensure clean database schemas are created before and dropped after all tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_deepcore.db"):
        try:
            os.remove("test_deepcore.db")
        except PermissionError:
            pass

@pytest.fixture
def db_session():
    """Provides a transactional database session for each test, rolling back changes on completion."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Provides a test HTTP client with get_db dependency overridden to use the test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
