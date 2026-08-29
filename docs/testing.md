# Ecosystem-wide Testing

OPERA modules are released independently, but forecasting pipelines depend on them working together. For example, `forecast_realtime` calls a model from `bvar` or `nowcast-midas`; `forecast_evaluation` validates and scores the result; and `forecast_combo` combines the forecasts. A change in one module can break a downstream pipeline.

This page explains how the ecosystem catches those breaks before they reach users. [Ecosystem Testing in Detail](testing_details.md) explains the tests and workflows for contributors who need to change them.

## The idea

`opera-eco` defines a known-good ecosystem: exact module versions and one shared test suite. Module repositories can add the shared contract and pipeline lanes to their existing `package-quality.yml` workflow. The workflow tests the candidate with the remaining modules at their pinned versions.

After a successful PyPI publication, the module's `update-ecosystem.yml` workflow opens or updates a pull request in `opera-eco` for its exact version pin. The normal `package-quality.yml` workflow tests that pull request against the complete pinned ecosystem before the pin is merged.

## What this means day to day

### Working on a feature branch in your module

Write code, run the module's own tests, and push as usual. Where the module's `package-quality.yml` includes the shared lanes, they run with the other quality checks.

### Opening a PR

Add the shared lanes to the module's existing `package-quality.yml`. The workflow installs the pinned ecosystem, replaces the pinned copy of the module with the working tree, and runs the shared suite. The pull-request check then reports whether the candidate is compatible with the pinned set.

When a result exposes an incompatibility, use the failure to decide whether the candidate needs revision or the compatible pin set needs updating in `opera-eco`. Verify any updated set in `opera-eco` before adopting it.

### Publishing a release

On a GitHub release, `publish-pypi.yml` builds and publishes the distribution to PyPI. Its successful completion triggers `update-ecosystem.yml`, which opens or updates the corresponding `opera-eco` pin pull request. The `opera-eco` pull-request checks test the published version with the other pinned modules.

### Upgrading the ecosystem

To adopt a module release, update its exact pin in `opera-eco`, regenerate any affected skill API descriptions, and run the shared suite. After the updated `opera-eco` release is published, module repositories use the new pin on their next CI run.

## What this gives the team

This arrangement gives the team three things:

- Package-quality checks can surface regressions before a merge.
- Each published release gets an end-to-end compatibility check before its
	pin is adopted.
- One version manifest answers which module versions work together.

The trade-off is a longer CI run for pull requests and releases. In return, users do not discover downstream breakages first.

## Where to go next

See [Ecosystem Testing in Detail](testing_details.md) for the packaged test layout, the DataFrame contract, module workflow structure, and the procedure for updating the pinned ecosystem.
