import threading

import psycopg
from apscheduler.schedulers.background import BackgroundScheduler
from langgraph.checkpoint.postgres import PostgresSaver
from followup_agent import api, batch, db, gmail, llm, mailer, recommend_batch, scheduler
from followup_agent.config import load_settings
from followup_agent.graph import build_graph
from followup_agent.events import crawl as events_crawl
from followup_agent.events.clean import html_to_text
from followup_agent.events.fetch import Fetcher
from followup_agent.events.sources import build_sources

settings = load_settings()

# One long-lived connection for the checkpointer (LangGraph manages it).
_checkpointer_cm = PostgresSaver.from_conn_string(settings.database_url)
checkpointer = _checkpointer_cm.__enter__()
checkpointer.setup()

# Tables are created by the .NET project's EF Core migrations, which run at
# backend startup (Program.cs) and own every table in this database — including
# the ones only this agent reads and writes. supervisord starts the backend
# first so the schema is in place before anything here touches it.


def _assess_fn(app):
    return llm.assess_and_draft(app, settings)


def _send_fn(*, to, subject, body):
    mailer.send_email(settings, to=to, subject=subject, body=body)


class _SerializedGraph:
    """Serialize every graph.invoke behind one lock.

    The nightly batch runs on an APScheduler background thread while uvicorn
    serves approve/reject on its own threads, and all of them share the single
    PostgresSaver checkpointer connection — which is not thread-safe. One global
    lock keeps only one invoke touching that connection at a time.
    # ponytail: global lock; switch to a PostgresSaver connection pool if
    # invoke contention ever becomes a throughput problem.
    """

    def __init__(self, graph):
        self._graph = graph
        self._lock = threading.Lock()

    def invoke(self, *args, **kwargs):
        with self._lock:
            return self._graph.invoke(*args, **kwargs)


graph = _SerializedGraph(
    build_graph(checkpointer, assess_fn=_assess_fn, send_fn=_send_fn)
)


def _conn_factory():
    return psycopg.connect(settings.database_url)


def _nightly_job():
    conn = psycopg.connect(settings.database_url)
    try:
        ids = batch.run_batch(conn, graph, age_days=settings.followup_age_days)
        conn.commit()
        print(f"[batch] created {len(ids)} follow-ups")
    finally:
        conn.close()


_gmail_fn = gmail.make_gmail_fn(settings)


def _extract_fn(email):
    return llm.extract_recommendation(email, settings)


def _reco_job():
    conn = psycopg.connect(settings.database_url)
    try:
        ids = recommend_batch.run_reco_batch(
            conn, gmail_fn=_gmail_fn, extract_fn=_extract_fn,
            user_id=settings.reco_user_id)
        conn.commit()
        print(f"[reco] created {len(ids)} recommendation(s)")
    except Exception as e:                     # a bad poll must not kill the scheduler
        conn.rollback()
        print(f"[reco] batch failed: {e}")
    finally:
        conn.close()


_fetcher = Fetcher(settings.events_user_agent)


def _events_extract_fn(text: str, url: str):
    return llm.extract_event(html_to_text(text), settings)


def _events_job():
    conn = psycopg.connect(settings.database_url)
    try:
        ids = events_crawl.run_events_batch(
            conn,
            sources=build_sources(settings, _fetcher),
            fetch_fn=_fetcher.get,
            extract_fn=_events_extract_fn,
        )
        conn.commit()
        print(f"[events] created {len(ids)} event(s)")
    except Exception as e:            # a bad crawl must not kill the scheduler
        conn.rollback()
        print(f"[events] batch failed: {e}")
    finally:
        conn.close()


app = api.create_app(settings, conn_factory=_conn_factory, graph=graph)

_sched = BackgroundScheduler()
scheduler.start_nightly(_sched, _nightly_job)
scheduler.start_interval(_sched, _reco_job, settings.reco_poll_minutes)
scheduler.start_hours(_sched, _events_job, settings.events_poll_hours)
_sched.start()
