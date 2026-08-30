# Contributor Guide

## Initial Setup

1. Fork and clone the repository:

```bash
git clone https://github.com/bank-of-england/opera-eco.git
cd opera-eco
```

2. Install the development dependencies:

```bash
pip install -e ".[dev,docs,modules,notebooks,test]"  # Install development dependencies.
```

3. Install the pre-commit hooks:

```bash
pre-commit install
```

Pre-commit runs the following checks when you commit changes:

- Ruff's linter, with automatic fixes where possible
- Ruff's formatter
- NumPy-style docstring validation with `pydoclint`
- Strict validation of the Marimo example

To run every hook across the repository without creating a commit, use:

```bash
pre-commit run --all-files
```

Pre-commit does not build the documentation site or distribution package. Run the commands in [Documentation](#documentation) and [Code Style](#code-style) when you need those checks.

### Updating Ecosystem Modules

1. Change the exact pins in the `modules` optional-dependency extra.
2. Install the package and all quality dependencies with:

   ```bash
   python -m pip install -e ".[dev,docs,modules,notebooks,test]"
   ```

Use the same interpreter for installation and testing to keep the environment aligned with the manifest.
3. Run the installed-version guard:

   ```bash
   pytest src/opera/tests/skills_tests/test_skill_api.py::test_installed_versions_match_manifest
   ```

4. Synchronize the generated API sections, then review the diff:

   ```bash
   opera skills sync-api
   git diff -- src/opera/skills
   ```

5. Update the guidance and snippets for changed APIs.
6. Run the snippet, contract, and pipeline lanes:

```bash
pytest -n auto -m skill_snippet
pytest -n auto -m contract
pytest -n auto -m pipeline
```

7. Bump `opera-eco`. Tag and release only after the module upgrade merges.

A generated API diff requires human review, even when every test passes. An empty API diff and passing snippets may merge under the normal approval policy.

4. Verify the installation:

```bash
pytest
```

## Development Workflow

### Branch Strategy

- **`main`**: Production-ready code
- **Feature branches**: `feature/your-feature-name`
- **Bug fixes**: `fix/issue-description`
- **Documentation**: `docs/topic-name`

## Protected Branches and Pull Requests

All contributions must be submitted through a pull request. The `main` branch is protected, so contributors cannot push changes directly to it. Create a branch from `main`, commit and push your changes there, then open a pull request targeting `main`. The required check is the `package-quality` workflow, which must pass before the pull request can merge. Automated dependency and release changes follow the same pull-request process.

### Creating a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### Keeping Your Branch Updated

```bash
git checkout main
git pull origin main
git checkout feature/your-feature-name
   git rebase main  # Merge main instead when necessary.
```

### Commit Your Changes

```bash
git add .
git commit -m "describe your changes"
git push  # Or specify the branch explicitly.
```

## Code Standards

### Code Style

Use Ruff for formatting and linting:

```bash
# Format the code.
ruff format .

# Check for lint issues.
ruff check .

# Fix issues that Ruff can resolve.
ruff check . --fix

# Check formatting without changing files.
ruff format --check .

# Build the package.
python -m build

# Build the documentation.
zensical build
```

## Documentation

The documentation site is built with Zensical. The end-to-end example is also maintained as a Marimo notebook in `examples/illustration_marimo.py`. Its Markdown export is checked into `docs/notebooks/illustration.md` and must be regenerated when the notebook changes.

Install the documentation dependencies in an existing development environment:

```bash
pip install -e ".[docs,notebooks]"
```

Regenerate the notebook documentation explicitly when needed:

```bash
marimo export md examples/illustration_marimo.py \
   --output docs/notebooks/illustration.md \
   --flavor pymdown \
   --force
```

Build the complete documentation site locally, including strict validation:

```bash
zensical build --clean --strict
```

Continuous integration regenerates `docs/notebooks/illustration.md` and fails when the export changes. The checked-in notebook documentation therefore stays current.

### Naming Conventions

- **Variables**: `snake_case`
- **Functions/methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private functions/methods**: `_leading_underscore`

## Submitting Changes

### Before Submitting

1. Open an issue to discuss the bug or feature.
2. Use the issue number in the branch name, for example `fix/1-prior`.
3. Make the change and add an appropriate test.
4. Format, document, and test the code:

```bash
ruff format
ruff check .
pytest
```

5. Commit and push the changes:

```bash
git add .
git commit -m "fix: describe your changes"
git push origin fix/#1-prior
```

6. Submit a pull request.

## Creating a Release (for maintainers)

Release Please watches `main` for Conventional Commits. It opens or updates a release pull request with the next version and changelog entries. The commit subject must have a recognized type, such as `fix:`, `feat:`, or `deps:`; an untyped subject is ignored even when its body contains a `Release-As: ...` footer. A `Release-As: 0.4.5` footer is useful for a one-time release because it overrides the proposed version after the commit has been parsed. It does not make an otherwise untyped commit releasable.

After the release, dependency pin pull requests use `deps: ...` commits and produce normal patch releases. For example, a pin update after `0.4.5` produces `0.4.6`; `feat:` produces a minor release and a breaking change produces a major release. The release workflow enables auto-merge on the Release Please pull request; GitHub merges it after the required quality checks and branch protection rules pass. Keep work on `dev` until it is ready for the automatic release path through `main`.

Configure the `RELEASE_PLEASE_TOKEN` repository secret with a token that can write contents, issues, pull requests, tags, and releases. A token with those permissions is required so the Release Please pull request and release can trigger the downstream publication and documentation workflows. Enable **Allow auto-merge** in the repository settings and configure the package-quality check as required for `main`. Required human reviews must not apply to these automation pull requests unless the token's identity is allowed to bypass that rule. The workflows request auto-merge only for module pin and Release Please pull requests; all other pull requests remain manual.

Before merging a change into `main`, run the quality checks locally:

```bash
ruff check .
ruff format --check .
pre-commit run --all-files
marimo export md examples/illustration_marimo.py \
   --output docs/notebooks/illustration.md \
   --flavor pymdown \
   --force
git diff --exit-code -- docs/notebooks/illustration.md
zensical build --clean --strict
pytest
```

When GitHub auto-merges the Release Please pull request, Release Please creates the version tag and GitHub release. The published release starts these workflows:

- `publish-pypi.yml` builds the distribution and publishes it to PyPI.
- `deploy-docs.yml` builds the documentation site and deploys it to GitHub Pages.

Release Please updates `CHANGELOG.md`; do not edit generated release sections by hand. The PyPI and documentation workflows also support manual dispatch for an existing tag.

### Module pin pull requests

Each module repository must have an `update-ecosystem.yml` workflow that runs after its `Publish to PyPI` workflow succeeds. It reads the released version, updates only that module's exact pin in `opera-eco`, and opens or updates a pull request. The workflow enables auto-merge, and the `opera-eco` package-quality workflow validates the complete pinned set before GitHub merges the pull request.

Configure an `OPERA_ECO_PR_TOKEN` secret in each module repository. Use a fine-grained token or GitHub App token with read/write access to `Contents` and `Pull requests` in `bank-of-england/opera-eco`. The default token from the module repository cannot push a branch or open a pull request in another repository.

The update workflow uses one stable branch per module. A later release of the same module updates its existing pull request, while releases of different modules use separate branches and pull requests.
