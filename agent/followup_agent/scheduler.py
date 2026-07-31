def start_nightly(scheduler_obj, job) -> None:
    scheduler_obj.add_job(job, "cron", hour=9, minute=0)


def start_interval(scheduler_obj, job, minutes: int) -> None:
    scheduler_obj.add_job(job, "interval", minutes=minutes)
