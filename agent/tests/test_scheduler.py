from followup_agent import scheduler


class FakeScheduler:
    def __init__(self): self.jobs = []
    def add_job(self, func, trigger, **kw):
        self.jobs.append((func, trigger, kw))


def test_start_nightly_registers_daily_cron():
    s = FakeScheduler()
    job = lambda: None
    scheduler.start_nightly(s, job)
    assert len(s.jobs) == 1
    func, trigger, kw = s.jobs[0]
    assert func is job
    assert trigger == "cron"
    assert kw.get("hour") == 9
    assert kw.get("minute") == 0
