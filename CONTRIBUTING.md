# Contributing to opera-eco

## 1. Set up your fork

Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-github-user>/opera-eco.git
cd opera-eco
```

Add the main repository as `upstream` so you can fetch its latest changes:

```bash
git remote add upstream https://github.com/bank-of-england/opera-eco.git
```

Create and activate a Python 3.11 or newer environment, then install the package and all contributor dependencies:

```bash
python -m pip install -e ".[dev]"
```

The `dev` extra includes the pinned ecosystem modules, test dependencies, documentation and notebook tools, and quality checks.

Install the pre-commit hooks:

```bash
pre-commit install
```

The hooks run Ruff linting and formatting checks, NumPy-style docstring checks with `pydoclint`, a strict Zensical documentation build, and strict validation of the Marimo example. Run them across the repository with:

```bash
pre-commit run --all-files
```

Pre-commit does not run pytest or build the distribution. See [Run the checks](#3-run-the-checks) for the remaining commands.

## 2. Develop a change

The `dev` branch is the integration branch. Create feature, fix, and documentation branches from `upstream/dev`, then open pull requests back to `dev`. The protected `main` branch contains released code and receives changes through maintainer pull requests from `dev`.

```bash
git fetch upstream
git switch -c fix/123-short-description upstream/dev
```

Use branch names such as `feature/<issue>`, `fix/<issue>`, and `docs/<topic>`. Add or update tests and documentation with the implementation.

Use [Conventional Commits](https://www.conventionalcommits.org/) for commit subjects. Common types are `fix:`, `feat:`, `deps:`, `docs:`, and `chore:`. Release Please uses these subjects to build the changelog.

When the change is ready, push the branch to your fork:

```bash
git push -u origin fix/123-short-description
```

## 3. Run the checks

Run the local hooks and test suite before opening a pull request:

```bash
pre-commit run --all-files
pytest
```

The package-quality workflow also builds the distribution, validates generated files, builds the documentation in strict mode, and runs each test lane. To reproduce those checks locally:

```bash
python -m build
python -m twine check dist/*

marimo check --strict examples/illustration_marimo.py
marimo export md examples/illustration_marimo.py \
	--output docs/notebooks/illustration.md \
	--flavor pymdown \
	--force
git diff --exit-code -- docs/notebooks/illustration.md

zensical build --clean --strict

pytest src/opera/tests/skills_tests/test_skill_api.py::test_external_installed_versions_match_manifest
opera skills sync-api
git diff --exit-code -- src/opera/skills

pytest -n auto -m skill_snippet
pytest -n auto -m contract
pytest -n auto -m pipeline
```

Run the complete set when changing packaging, generated documentation, ecosystem pins, shared contracts, or pipelines. For a smaller change, run the checks relevant to the affected area in addition to pre-commit and pytest.

### Documentation

The site uses Zensical. The source files live in `docs/`, and the generated site in `site/` should not be edited by hand.

The end-to-end Marimo example lives in `examples/illustration_marimo.py`. When it changes, regenerate and commit `docs/notebooks/illustration.md` with the export command above. Continuous integration regenerates the file and fails if it differs from the committed version.

### Updating ecosystem modules

The `modules` optional-dependency group in `pyproject.toml` is the integration manifest for compatible OPERA releases. To update a module:

1. Change its exact version pin in `pyproject.toml`.
2. Reinstall the contributor environment with `python -m pip install -e ".[dev]"`.
3. Run the installed-version test listed above.
4. Run `opera skills sync-api` and review every change under `src/opera/skills/`.
5. Update affected guidance and snippets.
6. Run the `skill_snippet`, `contract`, and `pipeline` test lanes.

Generated API changes require human review even when every test passes.

OPERA module repositories normally open or update these pin pull requests after publishing a release. Their `update-ecosystem.yml` workflows use a stable branch per module, allowing a later release to refresh an existing pull request.

## 4. Submit a pull request

Before opening a pull request:

1. Link the issue that the change addresses.
2. Add an appropriate test for behavior changes.
3. Update affected documentation and generated files.
4. Run the relevant checks above.
5. Open the pull request against `dev`.

Pull requests to `dev` or `main` run the **Package quality** workflow. It builds and inspects the package, runs pre-commit, checks the Marimo source and generated documentation, builds the documentation site, validates module pins and generated skill APIs, and runs the snippet, contract, and pipeline suites.

## 5. Release a version (maintainers)

When `dev` is ready to release, open a pull request from `dev` to `main`. Merging it starts [Release Please](https://github.com/googleapis/release-please), which opens or updates a release pull request containing the next package version and generated `CHANGELOG.md` entries.

This repository uses the `always-bump-patch` strategy, so normal releases increment the patch version. A `Release-As: <version>` footer on a typed commit provides a one-time override. Do not edit generated release sections in `CHANGELOG.md` by hand.

Release Please enables auto-merge for its pull request. After the required checks and branch protection rules pass, merging that pull request creates the version tag and GitHub release. Publishing the release starts two workflows:

- **Publish to PyPI** builds, validates, and publishes the distribution.
- **Deploy Documentation to GitHub Pages** builds and deploys the Zensical site.

Both workflows can also be dispatched manually for an existing ref.