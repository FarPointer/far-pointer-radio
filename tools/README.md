# Tools

Custom scripts and utilities, plus forks of third-party tools used in radio production.

## Subdirectories

| Directory | Contents |
|---|---|
| `python/` | Python scripts and packages |
| `powershell/` | PowerShell scripts and modules |

## Python Requirements

Python 3.11 or later is required, with [`uv`](https://docs.astral.sh/uv/) managing
environments. Each package declares its dependencies in its own `pyproject.toml`; run the
pipelines through `tools/python/Makefile` so the required ordering lives in one place.

## PowerShell Requirements

PowerShell 7+ (cross-platform). Scripts are compatible with macOS, Linux, and Windows.
