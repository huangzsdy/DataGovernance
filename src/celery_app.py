from celery import Celery
from src.utils.logger import logger

def create_celery_app() -> Celery:
    """Create and configure Celery application"""
    app = Celery(
        'text_split_processor',
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/1',
        include=['src.tasks']
    )

    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        task_soft_time_limit=3000,
    )

    logger.info("Celery app created successfully")
    return app

celery_app = create_celery_app()