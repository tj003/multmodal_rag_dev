import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import supabase, s3_client, BUCKET_NAME
from auth import get_current_user
from tasks import process_document
router = APIRouter(tags=["files"])

class FileUploadRequest(BaseModel):
    filename: str
    file_size: int
    file_type: str

@router.get("/api/projects/{project_id}/files")
async def get_project_files(
    project_id:str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        # get all files for this project - FK constraint ensure project exists and belongs to the user 
        result = supabase.table("project_documents").select("*").eq("project_id", project_id).eq("clerk_id", clerk_id).order("created_at", desc=True).execute()

        return {
            "message": "Project Files retrieved successfully",
            "data" : result.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project Files: {str(e)}")
    
@router.post("/api/projects/{project_id}/files/upload-url")
async def get_upload_url(
    project_id: str,
    file_request: FileUploadRequest,
    clerk_id: str = Depends(get_current_user)
):
    try:
        #verify project exists and belongs to user
        project_result = supabase.table("projects").select("id").eq("id", project_id).eq("clerk_id", clerk_id).execute()

        if not project_result.data:
            raise HTTPException(status_code=400, detail="Project not found or access denied")

        #generate unique S3 key for the file - we can use a combination of project_id, clerk_id and filename to ensure uniqueness. In production, we might want to add a random uuid as well to guarantee uniqueness    
        file_extension = file_request.filename.split(".")[-1] if file_request.filename else ''
        unique_id = str(uuid.uuid4())
        s3_key = f"projects/{project_id}/documents/{unique_id}.{file_extension}"

        # generate presigned URL for direct upload to S3  (expire in 1 hr)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params= {
                "Bucket": BUCKET_NAME,
                "Key": s3_key,
                "ContentType": file_request.file_type
            },
            ExpiresIn = 3600 # expires in 1 hour

        )
        # create database record with pending status

        document_result = supabase.table("project_documents").insert({
            "project_id" : project_id,
            "filename": file_request.filename,
            "s3_key": s3_key,
            "file_size": file_request.file_size,
            "file_type": file_request.file_type,
            "processing_status": "uploading",
            "clerk_id": clerk_id
        }).execute()

        if not document_result.data:
            raise HTTPException(status_code=500, detail="Failed to create document record in database")

        return {
            "message": "Presigned URL generated successfully",
            "data": {
            "upload_url": presigned_url,
            "s3_key": s3_key,
            "document_id": document_result.data[0]
            },
         }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")
    
@router.post("/api/projects/{project_id}/files/confirm")
async def confirm_file_upload(
    project_id: str,
    confirm_request: dict,
    clerk_id: str = Depends(get_current_user)
):
    try:
        s3_key = confirm_request.get("s3_key")

        if not s3_key:
            raise HTTPException(status_code=400, detail="Missing s3_key in request")
        
        # update document status
        result = supabase.table("project_documents").update({
            "processing_status": "queued"
        }).eq("s3_key", s3_key).eq("project_id", project_id).eq("clerk_id", clerk_id).execute()

        document = result.data[0]
        document_id = document['id']
        if not result.data:
            raise HTTPException(status_code=404, detail="document not found or access denied")
        
        # start background preprocessing task - in production, we would likely push a message to a queue here for asynchronous processing by a worker. For simplicity, we'll just simulate this with a print statement
        
        task = process_document.delay(document_id)

        # store the Celery task ID in the database so we can track the status of the task later if needed
        supabase.table("project_documents").update({
            "task_id": task.id
        }).eq("id", document_id).execute()
        
        
        return {
            "message": "File upload confirmed, processing started with Celery Worker",
            "data": document
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm file upload: {str(e)}")

class UrlAddRequest(BaseModel):
    url: str

@router.post("/api/projects/{project_id}/files/url")
async def add_website_url(
    project_id: str,
    url_request: UrlAddRequest,
    clerk_id: str = Depends(get_current_user)
):
    try:
        url = url_request.url.strip()

        if not url.startswith(('http://', 'https://')):
            url = "https://" + url

        result = supabase.table("project_documents").insert({
            "project_id": project_id,
            "filename": url,  # we can store the URL in the filename field for simplicity
            "s3_key": "",  # no S3 key since this is a URL
            "file_size": 0,
            "file_type": "text/html",
            "processing_status": "queued",
            "source_type": "url",
            "source_url": url,
            "clerk_id": clerk_id
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to add URL to database")
        
        # start background processing task for the URL - in production, we would likely push a message to a queue here for asynchronous processing by a worker. For simplicity, we'll just simulate this with a print statement
        # start background preprocessing task - in production, we would likely push a message to a queue here for asynchronous processing by a worker. For simplicity, we'll just simulate this with a print statement
        document = result.data[0]
        document_id = document['id']
        task = process_document.delay(document_id)

        # store the Celery task ID in the database so we can track the status of the task later if needed
        supabase.table("project_documents").update({
            "task_id": task.id
        }).eq("id", document_id).execute()
        return {
            "message" : "URL added successfully, processing started with Celery Worker",
            "data": result.data[0]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add URL: {str(e)}")
    
@router.delete("/api/projects/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str,
    file_id: str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        # get the files record also verify it belongs to the user and project [ clerk id is FK in the table, so we can verify ownership and existence in one query
        file_result = supabase.table("project_documents").select("*").eq("id", file_id).eq("clerk_id", clerk_id).eq("project_id", project_id).execute()
        if not file_result.data:
            raise HTTPException(status_code=404, detail="File not found or access denied")
        file_record = file_result.data[0]
        # delete from S3 if it's a file upload (if s3_key exists)
        s3_key = file_record.get("s3_key")

        # delete from S3 (only if it's a file upload, not a URL)
        if s3_key:
            try:
                s3_client.delete_object(Bucket=BUCKET_NAME, Key =s3_key)
                print(f"Deleted file from S3: {s3_key}")
            except Exception as e:
                print(f"Failed to delete file from S3: {str(e)}")

        # delete the database record
        delete_result = (
            supabase.table("project_documents")
            .delete()
            .eq("id", file_id)
            .execute()
        )
        if not delete_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete file record from database")
        
        return {
            "message": "File deleted successfully",
            "data": delete_result.data[0]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
        
@router.get("/api/projects/{project_id}/files/{file_id}/chunks")
async def get_document_chunks(
    project_id: str,
    file_id: str,
    clerk_id: str= Depends(get_current_user)
):
    try:
        project_result = supabase.table('projects').select('id').eq('id', project_id).eq('clerk_id', clerk_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        doc_result = supabase.table('project_documents').select('id').eq('id', file_id).eq('project_id', project_id).execute()

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        chunk_result = supabase.table('document_chunks').select('*').eq('document_id', file_id).order('chunk_index').execute()

        return {
            "message": "Document chunks retrieved successfully",
            "data": chunk_result.data or []
        }
    except Exception as e:
        print(f"Error retrieving document chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document chunks: {str(e)}")