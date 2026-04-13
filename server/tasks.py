from celery import Celery
from database import supabase
import time
celery_app = Celery(
    'document_processor', # Name of the Celery application
    broker = "redis://localhost:6379/0", # Redis broker URL and  0 means using the first database in Redis [ task are queue]
    backend = "redis://localhost:6379/0" #store results in the same Redis database
) 

@celery_app.task
def process_document(document_id: str):
    """Document processing task that simulates a time-consuming operation."""
    try:
        doc_result = supabase.table("project_documents").select("*").eq("id", document_id).execute()
        document = doc_result.data[0]
        # step 1 : download the file from s3 and do partition 

        # step 2: chunk elements

        # step 3: summariziing each chunk

        # step 4 : vectorizing and storin

    except Exception as e:
        pass

def download_and_partition()


