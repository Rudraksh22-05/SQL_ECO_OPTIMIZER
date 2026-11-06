
import psycopg2

from app.config import settings


def get_connection():
    """Connection to the main application database."""
    return psycopg2.connect(settings.database_url)


def get_benchmark_connection():
    """Connection to the isolated benchmark database."""
    return psycopg2.connect(settings.benchmark_database_url)