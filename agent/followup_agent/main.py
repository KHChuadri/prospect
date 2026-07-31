import threading

import psycopg
from apscheduler.schedulers.background import BackgroundScheduler
from langgraph.checkpoint.postgres import PostgresSaver
from followup_agent import api, batch, db, gmail, llm, mailer, recommend_batch, scheduler
from followup_agent.config import load_settings
from followup_agent.graph import build_graph

settings = load_settings()

# One long-lived connection for the checkpointer (LangGraph manages it).
_checkpointer_cm = PostgresSaver.from_conn_string(settings.database_url)
checkpointer = _checkpointer_cm.__enter__()
checkpointer.setup()

# Ensure agent-owned tables exist.
with psycopg.connect(settings.database_url) as _c:
    db.init_schema(_c)
    db.init_ai_schema(_c)
    db.init_reco_schema(_c)
    _c.commit()


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


app = api.create_app(settings, conn_factory=_conn_factory, graph=graph)

_sched = BackgroundScheduler()
scheduler.start_nightly(_sched, _nightly_job)
scheduler.start_interval(_sched, _reco_job, settings.reco_poll_minutes)
_sched.start()
