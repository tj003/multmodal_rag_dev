from celery import Celery
from database import supabase
import time
from database import supabase, s3_client, BUCKET_NAME
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
import os
import tempfile

celery_app = Celery(
    'document_processor', # Name of the Celery application
    broker = "redis://localhost:6379/0", # Redis broker URL and  0 means using the first database in Redis [ task are queue]
    backend = "redis://localhost:6379/0" #store results in the same Redis database
) 

def update_status(document_id: str, status: str, details: dict = None):
    """update document processing status with optional details"""

    # get current document
    result = supabase.table("project_documents").select("*").eq("id", document_id).execute()

    # start with exisiting details or empty dict
    current_details = {}

    if result.data and result.data[0]["processing_details"]:
        current_details = result.data[0]["processing_details"]

    # add new details if provided
    if details:
        current_details.update(details)

    # update table
    supabase.table("project_documents").update({
        "processing_status": status,
        "processing_details": current_details

    }).eq("id", document_id).execute()
    
@celery_app.task
def process_document(document_id: str):
    """Document processing task that simulates a time-consuming operation."""
    try:
        doc_result = supabase.table("project_documents").select("*").eq("id", document_id).execute()
        document = doc_result.data[0]
        # step 1 : download the file from s3 and do partition 
        update_status(document_id, "partitioning")

        elements = download_and_partition(document_id, document)

        tables = sum (1 for e in elements if e.category == "Table")
        images = sum (1 for e in elements if e.category == "Image")
        text_elements = sum (1 for e in elements if e.category in ["NarrativeText", "Title", "Text"])
        print (f" Extracted: {tables} tables, {images} images, {text_elements} text elements")

        # step 2: chunk elements
        chunks, chunking_metrics = chunk_elements(elements)
        update_status(document_id, "summarising", {
            "chunking": chunking_metrics
        })

        # step 3: summariziing each chunk
        

        # step 4 : vectorizing and storing
        
        return {
            "status": "success",
            "document_id": document_id
        }

    except Exception as e:
        print(f"Error: {e}")
        update_status(document_id, "failed", {"error": str(e)})  # ✅ also add this
        raise  # Re-raise so Celery marks the task as FAILED, not succeeded

def download_and_partition(document_id: str, document: str):
    """Download document from S3 / Cral URL and partition into elements"""

    print(f"Downloading and partitioning document {document_id}")

    source_type = document.get("source_type", "file")

    if source_type == "url":
        # crwal the url and get the content
        pass
    else:
        # handle file processing
        s3_key = document["s3_key"]
        filename = document["filename"]
        file_type = filename.split(".")[-1].lower()
        #download the file from s3 and save it to a temp location
        temp_file = os.path.join(tempfile.gettempdir(), f"{document_id}.{file_type}")

        try:
            s3_client.download_file(BUCKET_NAME, s3_key, temp_file)
            elements = partition_document(temp_file, file_type, source_type="file")
            element_summary = analyze_summary(elements)
            update_status(document_id, "chunking", {
                "partitioning": {
            "elements_found": element_summary
                }
            })
            return elements
        finally:
            # Try cleaning up the .tmp variant unstructured leaves behind
            tmp_variant = os.path.splitext(temp_file)[0] + ".tmp"
            if os.path.exists(tmp_variant):
                os.remove(tmp_variant)
       

    return elements


def partition_document(file_path: str, file_type: str, source_type:  str = "file"):
    """Partition document based on file type and source type"""

    if source_type == "url":
        pass

    if file_type == "pdf":
        return partition_pdf(
            # filename=file_path,
            # strategy="hi_res", # use th emot accurate but slowest strategy to capture as much layout information as possible
            # infer_table_structure=False,# keep table structure in html
            # extract_image_block_types=["Image"], # grab images found in the pdf
            # extract_image_block_to_payload=True # extract images as base64 and include in the payload
            filename=file_path,
            strategy="hi_res",
            infer_table_structure=False,  # 🔥 Disable broken table model
            # hi_res_model_name="yolox",    # 🔥 Force working layout model
            pdf2image_poppler_path=r"C:\Users\tusha\poppler-24.08.0\Library\bin",
            extract_image_block_types=["Image"],
            extract_image_block_to_payload=True
        )


def analyze_summary(elements):
    """Count different types of elemetn found in the document and return """
    text_count = 0
    table_count = 0
    image_count = 0
    title_count = 0
    other_count = 0

    # Go through each element and count what type it is
    for elements in elements:
        element_name = type(elements).__name__ #get the class name like "Table" or "Narrative Text"

        if element_name in ["NarrativeText", "Text", "ListItem", "figureCaption"]:
            text_count += 1
        elif element_name in ["Table", "Header"]:
            table_count += 1
        elif element_name == "Image":
            image_count += 1
        elif element_name == "Title":
            title_count += 1
        else:
            other_count += 1    
    
    return {
        "text": text_count,
        "table": table_count,
        "image": image_count,
        "title": title_count,
        "other": other_count
    }

def chunk_elements(elements):
    "Chunks elements using title-based strategy and collect metrics"

    print(" Creating smart chunks...")

    chunks = chunk_by_title(
        elements,
        max_characters = 3000,
        new_after_n_chars = 2400,
        combine_text_under_n_chars = 500
    )

    # collect chunking metrics
    total_chunks = len(chunks)

    chunking_metrics = {
        "total_chunks" : total_chunks
    }

    print (f" Created {total_chunks} chunks from {len(elements)} elements")

    return chunks, chunking_metrics