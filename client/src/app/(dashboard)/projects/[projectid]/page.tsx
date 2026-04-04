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

interface ProjectPageProps{
    params: Promise<{
        projectId: string;
    }>;
    }


function ProjectPage({ params }:ProjectPageProps) {
    const { projectId } = use(params);
    const { getToken, userId } = useAuth();

    // data

    const [data, setData] = useState({
        project: null,
        chats: [],
        documents: [],
        settings: null
    })

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null);
     
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
                setError("Failed to load project data. Please try again.")
            }

            
            finally {
                setLoading(false);
            }
             
    };
    loadAllData();
    },[userId, projectId]);
   

    //chat related method
    const handleCreateNewChat = async () =>{
        console.log("Creating new chat for project:");
    };
    const handleDeleteChat = async (chatId: string) =>{
        console.log("Deleting chat with id:", chatId);
    }
    const handleChatClick = async (chatId: string) => {
        console.log("Navigating to chat:", chatId);
    };
    const handleDocumentUpload = async (files : File) =>{
        console.log("Upload Files", files);
    }
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
    };
    const handlePublishSettings = async () =>{
        console.log("Make API call to publish settings")
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
        error = {null}
        loading = {false}
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