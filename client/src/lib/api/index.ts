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
    post: async(endpoint: string, data: any, token: string|null) => {
            const headers :HeadersInit  = {
                "Content-Type": "application/json",
            };
            if(token){
                headers["Authorization"] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}${endpoint}`,{
                headers,
                method: "POST",
                body: JSON.stringify(data),
            });

            if(!response.ok){
                throw new Error(`API request failed with status ${response.status}`);
            }
            const responseJson: any = await response.json();
            return responseJson;
    },
    delete:async(endpoint: string, token: string|null) => {
        const headers :HeadersInit  = {};
        if(token){
            headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`,{
            headers,
            method: "DELETE",
        });

        if(!response.ok){
            throw new Error(`API request failed with status ${response.status}`);
        }
        const responseJson: any = await response.json();
        return responseJson;
    },
    put: async(endpoint: string, data: any, token: string|null) => {
            const headers :HeadersInit  = {
                "Content-Type": "application/json",
            };
            if(token){
                headers["Authorization"] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE_URL}${endpoint}`,{
                headers,
                method: "PUT",
                body: JSON.stringify(data),
            });

            if(!response.ok){
                throw new Error(`API request failed with status ${response.status}`);
            }
            const responseJson: any = await response.json();
            return responseJson;
    },
    uploadToS3: async(url: string, file: File) => {
        const response = await fetch(url, {
            method: "PUT",
            body: file,
            headers: {"Content-Type": file.type},
        });
        if (!response.ok){
            throw new Error(`Failed to upload file to S3 with status ${response.status}`);

        }
        return response;
    }

};