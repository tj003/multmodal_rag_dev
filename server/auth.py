import os
from fastapi import HTTPException, Request
from dotenv import load_dotenv
from clerk_backend_api import Clerk
from clerk_backend_api import AuthenticateRequestOptions
load_dotenv()
#initilize clerk clinet
clerk_client = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

async def get_current_user(request: Request)-> str:
    try:
        request_state = clerk_client.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties = ALLOWED_ORIGINS
            )
        )
        print(request_state.payload)

        payload = request_state.payload
        if not request_state.is_signed_in:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        clerk_id = payload.get("sub")

        if not clerk_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return clerk_id
        

    except Exception as e:
        print("AUTH ERROR:", str(e))
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")