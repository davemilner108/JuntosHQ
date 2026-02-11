"""Seed the database with the original Philadelphia Junto (1727)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from juntos import create_app
from juntos.seed import run

app = create_app()
with app.app_context():
    run()
