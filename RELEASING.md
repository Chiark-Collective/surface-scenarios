# Releasing survi-scenarios

Minimal checklist to cut a new version to PyPI. The `.env` here already carries `PYPI_API_TOKEN` for automation.

1) Bump version  
   - Edit `pyproject.toml` `[project].version`.

2) Sanity + tests  
   - `PYTHONPATH=src pytest tests -q`

3) Build artifacts  
   - `python -m build`

4) Publish  
   - `python -m twine upload dist/* -u __token__ -p "$PYPI_API_TOKEN"`

5) Tag  
   - `git tag -a vX.Y.Z -m "survi-scenarios vX.Y.Z"` and push tags if desired.

6) Downstream update  
   - Update Survi to depend on the new version (drop file:// pin).
