# Ecosystem Testing in Detail

This page explains how OPERA tests compatibility across its independently released modules. Read [Ecosystem-wide Testing](testing.md) first for a shorter overview.

The design rests on one rule: test one candidate module against a known set of all the others. The exact versions and the shared tests both live in this repository, so every module uses the same definition of compatibility.

## How the pieces fit

```text
+========================== opera-eco ==========================+
|                                                                |
|  pyproject.toml       bundled skills       shared tests        |
|  exact module pins    API and examples     contracts/pipelines |
|         |                    |                    |            |
|         +--------------------+--------------------+            |
|                              |                                 |
|                              v                                 |
|                 +--------------------------+                   |
|                 | Package quality checks   |                   |
|                 +------------+-------------+                   |
|                              |                                 |
|                              v                                 |
|                     opera-eco[test]                            |
+============================+===================================+
                             |
                             | installed by module CI
                             v
+====================== module repository ======================+
|                                                                |
|  candidate working tree or wheel                                |
|               |                                                |
|               v                                                |
|  +----------------------------+                                |
|  | Test against pinned set    |                                |
|  +-------------+--------------+                                |
|                |                                               |
|                v                                               |
|  +----------------------------+                                |
|  | Contract and pipeline      |                                |
|  | tests                      |                                |
|  +-------------+--------------+                                |
|                |                                               |
|       +--------+--------+                                      |
|       |                 |                                      |
|     pass              fail                                     |
|       |                 |                                      |
|       v                 v                                      |
|  continue            report incompatibility                    |
+================================================================+
```

`opera-eco` owns the compatibility definition. A module repository can apply it by adding the shared test lanes to its existing `package-quality.yml`.

## Checks in `opera-eco`

The package quality workflow runs three pytest lanes in order:

| Marker | What it checks | Typical speed |
| --- | --- | --- |
| `skill_snippet` | Runs the Python examples embedded in the bundled skills | Seconds |
| `contract` | Checks schemas, generated API descriptions, package metadata, and snippet syntax | Seconds |
| `pipeline` | Runs model snapshots and cross-module forecasting flows | Minutes |

The workflow also runs `opera skills sync-api` and fails if that command changes a skill file. This gate keeps each skill's generated API description aligned with the pinned package version. The snippet lane then checks that the documented examples run.

### Packaged test layout

`src/opera/tests/` ships as package data. A module repository can therefore run the suite from its `package-quality.yml` without cloning `opera-eco`:

```text
src/opera/tests/
|-- conftest.py                 shared fixtures
|-- contracts/                 DataFrame schemas and invariants
|-- skills_tests/              API, metadata, and skill examples
`-- pipelines/                 model and cross-module flows
    |-- bvar/
    |-- ecosystem/
    |-- midas/
    |-- mixed_freq/
    `-- news/
```

Install and run the lanes separately when diagnosing a failure:

```bash
python -m pip install "opera-eco[test]"
pytest --pyargs opera.tests -m skill_snippet
pytest --pyargs opera.tests -m contract
pytest --pyargs opera.tests -m pipeline
```

The source checkout reads the integration manifest from its own
`pyproject.toml`. Packaged tests instead read the same exact pins from the
installed `opera-eco` distribution metadata. They never inspect the module
repository's `pyproject.toml`, which describes a different project. The
packaged `conftest.py` also registers OPERA's markers so module repositories do
not need to duplicate the marker configuration.

## Add Shared Lanes to a Module Workflow

To check a module against the pinned ecosystem, add the shared lanes to its existing `package-quality.yml`. The workflow first installs the pinned set, then replaces only the package under test:

```text
    1. Install the known-good set

         +----------------------------------+
         | A 1.2 | B 2.0 | C 3.4            |
         | installed by opera-eco[test]     |
         +----------------+-----------------+
                                            |
    2. Replace B only   |   candidate B: working tree or wheel
                                            |              |
                                            v              v
         +----------------------------------+
         | A 1.2 | B candidate | C 3.4      |
         | no other pinned module changes   |
         +----------------+-----------------+
                                            |
    3. Run shared tests v
         +----------------------------------+
         | contract tests + pipeline tests  |
         +----------------------------------+
```

For a working-tree check, install the candidate with:

```bash
python -m pip install -e . --force-reinstall --no-deps
```

`--no-deps` matters: it prevents the candidate's dependency declarations from silently replacing other pinned modules. A passing run therefore shows that the candidate works with the current ecosystem, not with a newly resolved set of dependencies.

The shared gate reads `[project].name` from the checked-out module's
`pyproject.toml` and excludes that candidate alone from exact version matching.
Its installed version is expected to differ from OPERA's pin while testing an
unreleased change. Every other ecosystem package must still match its pin, and
the candidate still participates in API, contract, and pipeline checks.

The release gate performs the same substitution with the built wheel. Testing the wheel catches packaging errors that an editable installation can hide, such as missing package data or incorrect entry points.

## DataFrame contracts

OPERA modules exchange long-format pandas DataFrames. `OutturnSchema` and `ForecastSchema` in [the schema module](../src/opera/tests/contracts/schema.py) define the required columns and coerce compatible input types.

Both schemas require these columns:

| Column | Contract |
| --- | --- |
| `date` | Period to which the value applies |
| `vintage_date` | Date on which the value became known; nullable for outturns |
| `variable` | Series identifier |
| `frequency` | `Q` or `M` |
| `value` | Numeric value; may be null |
| `metric` | `levels`, `pop`, or `yoy`; may be null |

Forecast frames also require:

| Column | Contract |
| --- | --- |
| `forecast_horizon` | Non-negative integer; `0` is the first forecast period |
| `source` | Producing model or module, such as `bvar` or `nowcast-midas` |

The schemas allow additional columns. A module may therefore retain useful derived values while still satisfying the shared contract.

## Recommended Module Workflow Integration

Use the module's existing `package-quality.yml` for normal working-tree checks. A module may also provide an `ecosystem.yml` workflow for additional candidate checks, but the shared suite does not need to run again during publication.

### Pull Requests and Branch Pushes

When a module chooses to enforce ecosystem compatibility before merge, add these steps to its `package-quality.yml`:

1. configures pip to use the package index;
2. installs `opera-eco[test]` and its pinned modules;
3. replaces the pinned copy of the current module with the working tree; and
4. runs the contract and pipeline lanes.

Make these required checks when the module's branch-protection policy calls for them.

### Releases: `publish-pypi.yml`

The publication workflow builds and publishes the distribution. Its successful completion triggers `update-ecosystem.yml`:

```text
    +-------------------------+
    | GitHub release          |
    +------------+------------+
                             |
                             v
    +-------------------------+
    | Build wheel and sdist   |
    +------------+------------+
                             |
                             v
    +-------------------------+
    | Ecosystem gate          |
    | install wheel; run tests|
    +------------+------------+
                             |
             +-------+-------+
             |               |
         pass            fail
             |               |
             v               v
    +----------+    +------------------+
    | Publish  |    | Stop publication |
    | to PyPI  |    |                  |
    +----+-----+    +------------------+
             |
             v
    +---------------------------+
    | update-ecosystem workflow |
    | opens or updates pin PR   |
    +-------------+-------------+
                  |
                  v
    +---------------------------+
    | opera-eco package quality |
    | tests the published pin   |
    +---------------------------+
```

The update workflow reads the published source version and opens or updates a pull request in `opera-eco`. The normal package-quality workflow tests that pull request before the new version is adopted by the pinned ecosystem.

## Update the pinned ecosystem

To adopt one or more module releases:

1. Change the exact versions in `pyproject.toml` under `[project.optional-dependencies].modules`.
2. Install the updated module set.
3. Run `opera skills sync-api` and review every generated API change.
4. Update affected guidance and snippets.
5. Run the snippet, contract, and pipeline lanes.
6. Open a pull request with the pin and documentation changes.

After the updated `opera-eco` release is published, module repositories pick up the new pins the next time they install `opera-eco[test]`.

## Why the tests live here

A separate `opera-contracts` package would split the version manifest from the tests that enforce it. Keeping both in `opera-eco` provides one package for CI, one compatibility manifest, and one review point for schema and pipeline changes. The `test` extra adds pytest, Pandera, and the other test dependencies only when a user requests it.

## Reference

| Concern | Source of truth |
| --- | --- |
| Compatible module versions | `[project.optional-dependencies].modules` in `pyproject.toml` |
| Shared schemas and tests | `src/opera/tests/` |
| Generated skill APIs | `src/opera/skills/`, checked by `opera skills sync-api` |
| Package quality gates | `.github/workflows/package-quality.yml` |
| Module pull-request gate | Shared lanes added to each module's `package-quality.yml` |
| Published-version pin updates | `update-ecosystem.yml` in each module repository |
