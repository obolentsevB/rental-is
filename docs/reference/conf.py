"""Конфігурація Sphinx для довідника коду rental-is."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

project = "rental-is"
language = "uk"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
exclude_patterns = ["_build"]

default_role = "code"

autodoc_member_order = "bysource"

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
