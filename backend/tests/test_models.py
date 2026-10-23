from sqlalchemy import create_engine
from app.db.base import Base
import app.db.models

def test_tables_create():
    engine= create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

def test_expected_tables_registered():
    assert {"modules", "issues", "issue_transitions"} <= set(Base.metadata.tables)