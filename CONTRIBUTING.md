# Development

Read [AGENTS.md](AGENTS.md) and the single permanent
[development handoff](docs/DEVELOPMENT_STATUS.md) before changing anything.
The handoff records exact source/check counts and owner acceptance separately.
[Provenance](docs/PROVENANCE.md) preserves the reused tested pricing implementation
and attribution. [Architecture](docs/ADR-001.md) and [API v1](docs/API.md) explain
producer ownership and the read-only consumer boundary.

Use Python 3.14.8 and hash-verified dependencies:

```sh
uv venv --python 3.14.8
uv pip sync --require-hashes requirements-dev.lock
.venv/bin/python tools/prepare_consumer_refs.py
.venv/bin/python tools/prepare_hacs_reference.py
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine -W error::ResourceWarning
.venv/bin/ruff check custom_components tests tools
.venv/bin/ruff format --check custom_components tests tools
.venv/bin/python tools/test_two_runtime.py --consumer pr26
.venv/bin/python tools/run_consumer_suite.py --consumer pr26
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
.venv/bin/python tools/build_beta.py
```

Repeat producer and unchanged consumer/runtime gates with requirements-ha-current.lock.
Prepare clean packages, install both ZIP layouts outside this repository, run actual
pinned HACS workflows and test the real native frontend before release. Never use
production HA or real charging equipment for these tests. A cloud SQLite benchmark
does not establish Raspberry Pi performance. Publication requires exact-source
successful CI, immutable tag and independently verified packages/checksums.
