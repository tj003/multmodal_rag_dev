import logging

#create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler("app.log")

logging.basicConfig(
                    level=logging.DEBUG, 
                    format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[console_handler,file_handler]
                    )

logging.debug("debug")
logging.info("info")
logging.warning("warning")
logging.error("error")
logging.critical("critical")