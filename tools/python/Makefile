# Task runner for the Python tools.
#
# Ordering is the whole point: the czcache steps have a required sequence, and it should
# live here rather than in anyone's memory. Every target runs through `uv`, which syncs
# each package's own pyproject.toml dependencies automatically.

CZCACHE := czcache
CZAUDIT := czaudit
CZARCHIVE := czarchive
CACHE := ../../shows/convergence-zone/playlists/cache

.PHONY: help build verify all missing-spins refresh-spinitron audit lint format test check clean

help:
	@echo "build            rebuild the playlist cache"
	@echo "verify           assert the cache invariants (non-zero exit on failure)"
	@echo "check            build + verify + assert the cache diff is empty"
	@echo "missing-spins    regenerate the missing-spins workbook and CSV"
	@echo "refresh-spinitron  re-snapshot Spinitron playlist IDs from the public page"
	@echo "all              refresh-spinitron, build, verify, missing-spins"
	@echo "audit            run the czaudit pipeline (OneNote extract + audit workbook)"
	@echo "lint             ruff check"
	@echo "format           ruff format"
	@echo "test             pytest"

build:
	cd $(CZCACHE) && uv run python build.py

verify:
	cd $(CZCACHE) && uv run python verify.py

# What CI runs. A rebuild that changes nothing must produce a zero-line diff -- that is
# what makes the cache reviewable in a pull request.
check: build verify
	git diff --exit-code -- $(CACHE)

refresh-spinitron:
	cd $(CZCACHE) && uv run python fetch_spinitron_playlists.py

missing-spins:
	cd $(CZCACHE) && uv run python build_missing_spins.py
	cd $(CZCACHE) && uv run python enrich_missing_spins.py

all: refresh-spinitron build verify missing-spins

audit:
	cd $(CZAUDIT) && uv run python extract.py
	cd $(CZAUDIT) && uv run python build_audit.py

lint:
	uvx ruff check .

format:
	uvx ruff format .

test:
	cd $(CZCACHE) && uv run --group dev pytest

clean:
	rm -rf $(CZCACHE)/reports $(CZCACHE)/__pycache__ $(CZAUDIT)/__pycache__
