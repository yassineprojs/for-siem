from ey_cs_monitor.main import within_quiet_hours

def test_quiet_hours_returns_bool():
    assert isinstance(within_quiet_hours("01:00", "03:00"), bool)
