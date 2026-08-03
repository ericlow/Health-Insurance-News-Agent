import logging
from scheduler import run_pipeline

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(event, context):
    run_pipeline()
