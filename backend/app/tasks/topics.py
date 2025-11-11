"""Background tasks related to topics."""

from celery import shared_task


@shared_task(name="topics.create")
def create_topic_task(payload: dict[str, str]) -> dict[str, str]:
    """Persist a topic payload.

    In a real implementation this would write to the database. For now it simply logs the
    payload and returns it so workers can be validated during integration testing.
    """

    # A placeholder side-effect that simulates work.
    return payload
