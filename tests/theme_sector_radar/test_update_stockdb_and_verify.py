from scripts.update_stockdb_and_verify import StockDBUpdateRunner


class FakeOps:
    def __init__(self, latest_dates):
        self.latest_dates = list(latest_dates)
        self.actions = []

    def get_latest_date(self):
        if len(self.latest_dates) > 1:
            return self.latest_dates.pop(0)
        return self.latest_dates[0] if self.latest_dates else None

    def is_running(self):
        self.actions.append("is_running")
        return True

    def stop_database(self):
        self.actions.append("stop_database")
        return True

    def start_updater(self):
        self.actions.append("start_updater")
        return True

    def start_database(self):
        self.actions.append("start_database")
        return True

    def sleep(self, seconds):
        self.actions.append(f"sleep:{seconds}")


def test_update_skips_when_stockdb_is_already_fresh():
    ops = FakeOps(["20260709"])
    runner = StockDBUpdateRunner(ops=ops, expected_date="20260709", wait_seconds=60, poll_seconds=10)

    result = runner.run()

    assert result["status"] == "already_fresh"
    assert result["latest_daily_date"] == "20260709"
    assert "start_updater" not in ops.actions


def test_update_stops_database_launches_updater_and_restarts_database():
    ops = FakeOps(["20260708", "20260708", "20260709"])
    runner = StockDBUpdateRunner(ops=ops, expected_date="20260709", wait_seconds=20, poll_seconds=10)

    result = runner.run()

    assert result["status"] == "updated"
    assert result["latest_daily_date"] == "20260709"
    assert ops.actions[:3] == ["stop_database", "start_updater", "sleep:10"]
    assert "start_database" in ops.actions


def test_update_times_out_when_latest_date_never_reaches_expected():
    ops = FakeOps(["20260708"])
    runner = StockDBUpdateRunner(ops=ops, expected_date="20260709", wait_seconds=20, poll_seconds=10)

    result = runner.run()

    assert result["status"] == "timeout"
    assert result["latest_daily_date"] == "20260708"
    assert result["expected_date"] == "20260709"
    assert "start_database" in ops.actions
