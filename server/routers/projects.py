from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import supabase
from auth import get_current_user
router = APIRouter(tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectSettings(BaseModel):
    embedding_model: str
    rag_strategy: str
    agent_type: str
    chunk_per_search: int
    final_context_size: int
    similarity_threshold: float
    number_of_queries: int
    reranking_enabled: bool
    reranking_model: str
    vector_weight: float
    keyword_weight: float


@router.get("/api/projects")
def get_projects(clerk_id: str = Depends(get_current_user)):
    try:
        result = supabase.table("projects").select("*").eq("clerk_id", clerk_id).execute()

        return {
            "message": "Projects retrieved successfully",
            "data" : result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve projects: {str(e)}")

@router.post("/api/projects")
def create_project(project: ProjectCreate, clerk_id: str = Depends(get_current_user)):
    try:
        project_result = supabase.table("projects").insert(
            {
                "name": project.name,
                "description": project.description,
                "clerk_id": clerk_id
            }
        ).execute()
        print("PROJECT RESULT:", project_result.data)

        if not project_result.data:
            raise HTTPException(status_code=500, detail="Failed to create project")

        created_project = project_result.data[0]
        project_id = created_project["id"]
        
        #create default column for the project
        setting_result = supabase.table("project_settings").insert(
            {
                "project_id": project_id,
                "embedding_model": "text-embedding-3-large",
                "rag_strategy": "basic",
                "agent_type": "agentic",
                "chunk_per_search": 10,
                "final_context_size": 5,
                "similarity_threshold": 0.3,
                "number_of_queries": 5,
                "reranking_enabled": True,
                "reranking_model":"rerank-english-v3.0",
                "vector_weight": 0.7,
                "keyword_weight": 0.3
            }
        ).execute()

        if not setting_result.data:
            # if settings creation files, we should clean up the project
            supabase.table("projects").delete().eq("id", project_id).execute()
            raise HTTPException(status_code=500, detail="Failed to create project settings")
        print("CREATED PROJECT:", created_project)
        print("CREATED SETTINGS:", setting_result.data)
        return {
            "message": "Project created successfully",
            "data": created_project
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
        
@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str, clerk_id: str = Depends(get_current_user)):
    try:
        # verify project access and belongs to user
        project_result = supabase.table("projects").select("*").eq("id",project_id).eq("clerk_id", clerk_id).execute()
        
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        #delete project ( CASCASDE handlesall related data)
        deleted_result = supabase.table("projects").delete().eq("id", project_id).eq("clerk_id", clerk_id).execute()

        if not deleted_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete project")
        
        return {
            "message": "Project deleted successfully",
            "data": deleted_result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")
    
@router.get("/api/projects/{project_id}")
async def get_project(
    project_id:str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        result = supabase.table("projects").select("*").eq("id", project_id).eq("clerk_id", clerk_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        return {
            "message": "Project retrieved successfully",
            "data" : result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project: {str(e)}")
    
@router.get("/api/projects/{project_id}/chats")
async def get_project_chats(
    project_id:str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        result = supabase.table("chats").select("*").eq("project_id", project_id).eq("clerk_id", clerk_id).order("created_at", desc=True).execute()

        return {
            "message": "Project Chats retrieved successfully",
            "data" : result.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project chats: {str(e)}")

@router.get("/api/projects/{project_id}/settings")
async def get_project_settings(
    project_id:str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        settings_result = supabase.table("project_settings").select("*").eq("project_id", project_id).execute()

        if not settings_result.data:
            raise HTTPException(status_code=404, detail = f"Project settings not found for project_id: {project_id}")
        
        return {
            "message": "Project settings retrieved successfully",
            "data" : settings_result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project settings: {str(e)}")

@router.put("/api/projects/{project_id}/settings")
async def update_project_settings(
    project_id: str,
    settings: ProjectSettings,
    clerk_id: str = Depends(get_current_user)
):
    try:
        #first verify he project exists and belongs to the user
        project_result =supabase.table("projects").select("id").eq("id", project_id).eq("clerk_id", clerk_id).execute()

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Settings not found for this project")
        
        # Perform the update
        update_result = supabase.table("project_settings").update(settings.model_dump()).eq("project_id", project_id).execute()
        print("Updating settings for:", project_id)
        print("Payload:", settings.model_dump())
        print("Result:", update_result.data)
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update project settings")
        
        return {
            "message": "Project settings updated successfully",
            "data": update_result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project settings: {str(e)}")