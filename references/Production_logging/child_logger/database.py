import logging

db_logger = logging.getLogger(__name__)

def connect():
    db_logger.info("Connecting to database...")
    db_logger.info("Database connected successfully")

def query_users():
    db_logger.debug("Querying  all users from database")
    db_logger.info("Retrieved 5 user")