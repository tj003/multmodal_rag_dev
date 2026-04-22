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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage

# Initialize LLM for summarization
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

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
        source_type = document.get("source_type", "file")
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

        processed_chunks = summarise_chunks(chunks, document_id, source_type)

        

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

def summarise_chunks(chunks, document_id, source_type = "file"):
    """Transform chunks into searchable content with AI summaries"""
    processed_chunks = []
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        current_chunk = i + 1

        # update progress directly
        update_status(document_id, "summarising", {
            "summarising": {
                "current_chunk": current_chunk,
                "total_chunks": total_chunks
            }
        })

        # extract content from the chunk
        content_data = separate_content_types(chunk, source_type)

        # debug print
        print(f"Types found: {content_data['types']}")
        print(f"Tables {len(content_data['tables'])}, Images: {len(content_data['images'])}")

        # decide if we need to summarisation
        if content_data['tables'] or content_data['images']:
            print(f"Creating AI summary for mixed content...")
            enhanced_content = create_ai_summary(
                content_data['text'],
                content_data['tables'],
                content_data['images']
                )
        else:
            enhanced_content = current_chunk['text']

        # build the original _content structure
        original_content = {'text': content_data['text']}
        if content_data['tables']:
            original_content['tables'] = content_data['tables']
        if content_data['images']:
            original_content['images'] = content_data['images']

        # create processed chunk  withall data

        processed_chunk = {
            'content': enhanced_content,
            'original_content': original_content,
            'type': content_data['types'],
            'page_number': get_page_number(chunk, i),
            'char_count': len(enhanced_content)
        }

        processed_chunks.append(processed_chunk)

    print(f"Processed {len(processed_chunks)} chunks with AI enhancements")

    return processed_chunks

def get_page_number(chunk, chunk_index):
    """Get page number from chunk or use fallback"""
    if hasattr(chunk, 'metadata'):
        page_number = getattr(chunk.metadata, 'page_number', None)
        if page_number is not None:
            return page_number
    
    # Fallback: use chunk index as page number
    return chunk_index + 1


def separate_content_types(chunk, source_type="file"):
    """Analyze what types of content are in a chunk"""
    is_url_source = source_type == 'url'
    
    content_data = {
        'text': chunk.text,
        'tables': [],
        'images': [],
        'types': ['text']
    }
    
    # Check for tables and images in original elements
    if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
        for element in chunk.metadata.orig_elements:
            element_type = type(element).__name__
            
            # Handle tables
            if element_type == 'Table':
                content_data['types'].append('table')
                table_html = getattr(element.metadata, 'text_as_html', element.text)
                content_data['tables'].append(table_html)
            
            # Handle images (skip for URL sources)
            elif element_type == 'Image' and not is_url_source:
                if (hasattr(element, 'metadata') and 
                    hasattr(element.metadata, 'image_base64') and 
                    element.metadata.image_base64 is not None):
                    content_data['types'].append('image')
                    content_data['images'].append(element.metadata.image_base64)
    
    content_data['types'] = list(set(content_data['types']))
    return content_data

def create_ai_summary(text, tables_html, images_base64):
    """Create AI-enhanced summary for mixed content"""
    
    try:
        # Build the text prompt with more efficient instructions
        prompt_text = f"""Create a searchable index for this document content.

CONTENT:
{text}

"""
        
        # Add tables if present
        if tables_html:
            prompt_text += "TABLES:\n"
            for i, table in enumerate(tables_html):
                prompt_text += f"Table {i+1}:\n{table}\n\n"
        
        # More concise but effective prompt
        prompt_text += """
Generate a structured search index (aim for 250-400 words):

QUESTIONS: List 5-7 key questions this content answers (use what/how/why/when/who variations)

KEYWORDS: Include:
- Specific data (numbers, dates, percentages, amounts)
- Core concepts and themes
- Technical terms and casual alternatives
- Industry terminology

VISUALS (if images present):
- Chart/graph types and what they show
- Trends and patterns visible
- Key insights from visualizations

DATA RELATIONSHIPS (if tables present):
- Column headers and their meaning
- Key metrics and relationships
- Notable values or patterns

Focus on terms users would actually search for. Be specific and comprehensive.

SEARCH INDEX:"""
        
        # Build message content starting with the text prompt
        message_content = [{"type": "text", "text": prompt_text}]
        
        # Add images to the message
        for i, image_base64 in enumerate(images_base64):
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })
            print(f"🖼️ Image {i+1} included in summary request")
        
        message = HumanMessage(content=message_content)
        
        response = llm.invoke([message])
        
        return response.content
        
    except Exception as e:
        print(f" AI summary failed: {e}")