import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import supabase, s3_client, BUCKET_NAME
from auth import get_current_user

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
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")