# Integration tests

Place integration tests here and mark them with `@pytest.mark.integration`.
Tests requiring live credentials must also use `@pytest.mark.live_api`;
interactive Windows, desktop-automation, or hardware tests must use
`@pytest.mark.system`. The CI workflow excludes `live_api` and `system` tests.
Use temporary files and test doubles where possible.
