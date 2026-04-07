"use client";

import React, { use, useEffect, useState } from 'react'
import { ConversationsList } from '@/components/projects/ConversationsList';
import { KnowledgeBaseSidebar } from '@/components/projects/KnowledgeBaseSidebar';
import { FileDetailsModal } from '@/components/projects/FileDetailsModal';
import { useParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Settings } from 'lucide-react';
import { apiClient } from '@/lib/api/index';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { NotFound } from '@/components/ui/NotFound';
import { Preahvihear } from 'next/dist/compiled/@next/font/dist/google';
import toast from 'react-hot-toast';
import { Project, Chat, ProjectDocument, ProjectSettings } from "@/lib/types";

interface ProjectPageProps{
    params: Promise<{
        projectId: string;
    }>;
    }

interface ProjectData {
    project: Project | null;
    chats: Chat[];
    documents: ProjectDocument[];
    settings: ProjectSettings | null;
}


function ProjectPage({ params }:ProjectPageProps) {
    const { projectId } = use(params);
    const { getToken, userId } = useAuth();

    // data state 

    const [data, setData] = useState <ProjectData>({
        project: null,
        chats: [],
        documents: [],
        settings: null
    })

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null);

    const [isCreatingChat, setIsCreatingChat] = useState(false);
     
    //UI states
    const [activeTab, onSetActiveTab] = useState<"documents" | "settings">(
        "documents"
    );
    
    const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
        null
    );
    //  load all the data
    useEffect(() => {
        const loadAllData = async () => {
            if(!userId) return 
            
            try{
                setLoading(true);
                setError(null)    
                const token = await getToken(); 
                const [projectRes, chatsRes, documentRes , settingsRes] = await Promise.all([
                    apiClient.get(`/api/projects/${projectId}`,token),
                    apiClient.get(`/api/projects/${projectId}/chats`,token),
                    apiClient.get(`/api/projects/${projectId}/files`,token),
                    apiClient.get(`/api/projects/${projectId}/settings`,token),
            ]);
                setData({
                    project: projectRes.data,
                    chats: chatsRes.data,
                    documents: documentRes.data,
                    settings: settingsRes.data
                })
                }
            catch(err){
                console.error("Error loading project data", err);
                setError("Failed to load project data.")
                toast.error("Failed to load project data");
            }

            
            finally {
                setLoading(false);
            }
             
    };
    loadAllData();
    },[userId, projectId]);
   

    //chat related method
    const handleCreateNewChat = async () =>{
        if(!userId) return;

        try{
            setIsCreatingChat(true);

            const token = await getToken();
            
            const chatNumber = Date.now() % 10000; // simple way to generate a unique chat title

            const result = await apiClient.post(`/api/chats`,{
                title: `Chat #${chatNumber}`,
                project_id: projectId
            },token)

            const savedChat = result.data[0] 
            ///update local state with new chat
            setData((prev) => ({
                ...prev,
                chats: [savedChat, ...prev.chats]
            }))
            toast.success("Chat created successfully!");
        }
        catch(err){
            toast.error("Failed to create chat");
            console.error("Failed to create chat", err);
        }
        finally{
            setIsCreatingChat(false);
        }
    };
    const handleDeleteChat = async (chatId: string) =>{
        if (!userId) return;
        try{
            const token = await getToken();
            await apiClient.delete(`/api/chats/${chatId}`, token);

            //update local state by removing the deleted chat
            setData((prev) =>({
                ...prev,
                chats: prev.chats.filter((chat) => chat.id !== chatId),
            }));

            toast.success("Chat deleted successfully!");

        }
        catch(err){
            toast.error("Failed to delete chat");
            console.error("Failed to delete chat", err);
        }
        
    }
    const handleChatClick = async (chatId: string) => {
        console.log("Navigating to chat:", chatId);
    };
    const handleDocumentUpload = async (files  : File []) =>{
        console.log("Uploading Files", files);
        if(!userId) return;

            const token = await getToken();
            const uplaodDocuments = [];
            // proces all files parallelly 

            const uploadPromises = files.map(async (file) =>{
                try {
                    console.log("Requesting upload URL for file", file.name);
                    // step 1: get presigned url from backend
                    const uploadData = await apiClient.post(`/api/projects/${projectId}/files/upload-url`,{
                        filename: file.name,
                        file_size: file.size,
                        file_type: file.type,
                    },token)
                    const {upload_url, s3_key} = uploadData.data;

                    console.log("Received upload URL and S3 key from backend", {upload_url, s3_key});

                    // step 2: upload file to s3 using the presigned url
                    await apiClient.uploadToS3(upload_url, file);

                    //step 3: inform backend that upload is complete so it can update the database
                    await apiClient.post(`/api/projects/${projectId}/files/confirm`)
                } 
                catch(err){
                    console.error("Failed to get upload URL for file", file.name, err);
                    toast.error(`Failed to get upload URL for file ${file.name}`);
                    return null;
                }

        })
        };

    const handleDocumentDelete = async (documentId: string) => {
        console.log("Document Deleted");
    }
    const handleUrlAdd = async (url: string) => {
        console.log("Add URL", url);
    }
    const handleOpenDocument = (documentId: string) =>{
        console.log("Open document", documentId)
        setSelectedDocumentId(documentId);
    };

    // project settings
    const handleDraftSettings = (updates: any) => {
        console.log("Update local state with draft settings", updates)

        setData((prev) => {
            // If no settings exist yet, we can't draft updates, so we return previous state
            if(!prev.settings)
                {
                    console.log("Cannot update settings: not loaded yet");
                    return prev
                } 

            //merge the updated into existing settings
            return {
                ...prev,
                settings : {
                    ...prev.settings,
                    ...updates
                }
            }
        })
    };
    const handlePublishSettings = async () =>{
        console.log("Make API call to publish settings")
        if(!userId || ! data.settings){
            console.error("Cannot publish settings: missing user or settings data");
            toast.error("Cannot publish settings: missing user or settings data");
        }
        try{
            const token = await getToken();

            const result = await apiClient.put(`/api/projects/${projectId}/settings`, data.settings, token);
            setData((prev) =>({
                ...prev,
                settings: result.data
            }));
            toast.success("Settings saved successfully!");

        }
        catch(err){
            console.error("Failed to save settings", err);
            toast.error("Failed to save settings");
        }
    }

    if(loading){
        return <LoadingSpinner message="loading Project ..."/>
    }
    if(!data.project){
        return <NotFound message="Project not found"/>
    }

    const selectedDocument = selectedDocumentId ? data.documents.find(doc => doc.id == selectedDocumentId) : null;
     return( 
        <>
          <div> 
        <div className='flex h-screen bg-[#0d1117] gap-4 p-4'>
            <ConversationsList
        project = {data.project}
        conversations = {data.chats}
        error = {error}
        loading = {isCreatingChat}
        onCreateNewChat = {handleCreateNewChat}
        onChatClick = {handleChatClick}
        onDeleteChat = {handleDeleteChat}
        />
        {/* <KnowledgeBaseSidebar} */}
        <KnowledgeBaseSidebar
        activeTab = {activeTab}
        onSetActiveTab = {onSetActiveTab}
        projectDocuments= {data.documents}
        onDocumentUpload = {handleDocumentUpload}
        onDocumentDelete = {handleDocumentDelete}
        onOpenDocument = {handleOpenDocument}
        onUrlAdd = {handleUrlAdd}
        projectSettings = {data.settings}
        settingsError = {null}
        settingsLoading = {false}
        onUpdateSettings = {handleDraftSettings}
        onApplySettings = {handlePublishSettings}
        />
        </div>
        
     </div>
     { selectedDocument && (<FileDetailsModal 
     document={selectedDocument} 
     onClose={() => setSelectedDocumentId(null)}
     />
     )}
     </>
   );
    }
   
    

export default ProjectPage