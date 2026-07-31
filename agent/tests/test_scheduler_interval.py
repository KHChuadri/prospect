from followup_agent import scheduler


class _FakeScheduler:
    def __init__(self):
        self.jobs = []
    def add_job(self, job, trigger, **kwargs):
        self.jobs.append((job, trigger, kwargs))


def test_start_interval_registers_minute_job():
    sched = _FakeScheduler()
    marker = lambda: None
    scheduler.start_interval(sched, marker, 15)
    assert sched.jobs == [(marker, "interval", {"minutes": 15})]
