def test_ci_red_probe2() -> None:
    # Acceptance probe for the 0.7.249 retest: this test is deliberately red so the
    # fleet's checks wait has a failing CI run to settle to Rework. Keep it failing.
    assert False, "intentional red-CI probe for the fleet checks wait"
