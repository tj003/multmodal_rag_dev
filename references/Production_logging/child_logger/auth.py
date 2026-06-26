import logging

auth_logger = logging.getLogger(__name__)

def login(username):
    auth_logger.info(f"user {username} attemping to login")
    auth_logger.info(f"User {username} authenicated successfully")

def logout(username):
    auth_logger.info(f"User {username} logged out")