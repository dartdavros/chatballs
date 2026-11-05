"""Shared report reducers retain unknown durations and exact coverage."""

from dataclasses import replace

from chatballs.conversations.support_metrics import COUNTERS, DURATIONS
from chatballs.integrations.action_catalog.report_schemas import INTEGER
from chatballs.integrations.action_catalog.schema import BOOLEAN, obj
from chatballs.integrations.adapters.schema import TypeSpec

NUMBER = TypeSpec("number")
DURATION = obj(seconds=replace(NUMBER, nullable=True), observedSeconds=NUMBER,
    samples=INTEGER, currentIntervals=INTEGER, meanSeconds=replace(NUMBER, nullable=True))
METRICS = obj(complete=BOOLEAN,
    completeByMetric=obj(**{name: BOOLEAN for name in (*COUNTERS, *DURATIONS)}),
    values=obj(**{**{name: replace(INTEGER, nullable=True) for name in COUNTERS},
        **{name: DURATION for name in DURATIONS}}), observedCounts=obj(**{name: INTEGER for name in COUNTERS}))
