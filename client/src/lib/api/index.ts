// Basic API Client Fucntion with authentication support

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const apiClient = {
    get: async(endpoint: string, token: string|null) => {
        const headers :HeadersInit  = {};
        if(token){
            headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`,{
            headers,
        });

        if(!response.ok){
            throw new Error(`API request failed with status ${response.status}`);
        }
        const responseJson: any = await response.json();
        return responseJson;
},
};