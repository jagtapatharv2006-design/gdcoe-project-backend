"""
Celery configuration for HPPS system.
"""

from config import Config

# Celery configuration
broker_url = Config.CELERY_BROKER_URL
result_backend = Config.CELERY_RESULT_BACKEND

task_serializer = Config.CELERY_TASK_SERIALIZER
result_serializer = Config.CELERY_RESULT_SERIALIZER
accept_content = Config.CELERY_ACCEPT_CONTENT

timezone = Config.CELERY_TIMEZONE
enable_utc = Config.CELERY_ENABLE_UTC

# Task settings
task_track_started = True
task_time_limit = Config.ANALYSIS_TIMEOUT
task_soft_time_limit = Config.ANALYSIS_TIMEOUT - 60  # 1 minute buffer

# Result settings
result_expires = 3600  # 1 hour

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 50

# Task routes
task_routes = {
    'tasks.analyze_student_task': {'queue': 'analysis'},
    'tasks.analyze_batch_task': {'queue': 'analysis'},
    'tasks.match_job_task': {'queue': 'jobs'},
}
