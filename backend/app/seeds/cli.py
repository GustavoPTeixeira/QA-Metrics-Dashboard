import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
import app.db.models  # Garante que os modelos estão registrados
from app.seeds.generator import seed_database
from app.seeds.golden_dataset import (
    GOLDEN_EXPECTATIONS_DEFECTS,
    GOLDEN_EXPECTATIONS_TESTS,
)
def run_cli():
    parser = argparse.ArgumentParser(description="Seed QA Metrics Database with Golden Dataset")
    parser.add_argument(
        "--db-url",
        default="sqlite:///qa_metrics.db",
        help="Database URL (default: sqlite:///qa_metrics.db)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    print(f"Connecting to database: {args.db_url}")
    engine = create_engine(args.db_url)
    # Garante que as tabelas existem no banco
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        print(f"Seeding database with deterministic seed={args.seed}...")
        seed_database(session, seed=args.seed)
        print("Done! Database successfully populated.")
        print(f"- Total Issues: {GOLDEN_EXPECTATIONS_DEFECTS.total_issues}")
        print(f"- Total Test Runs: {GOLDEN_EXPECTATIONS_TESTS.total_runs}")
        print(f"- Total Test Cases: {GOLDEN_EXPECTATIONS_TESTS.total_executed_tests}")
if __name__ == "__main__":
    run_cli()