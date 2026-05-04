from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import supabase
from auth import get_current_user
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Dict, Tuple
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from database import s3_client, BUCKET_NAME
import base64
load_dotenv()

llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",  # current vision model
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    output_dimensionality=768  # ← truncates to 768, HNSW compatible 
)

router = APIRouter(tags=["chats"])


class ChatCreate(BaseModel):
    title: str
    project_id: str

@router.post("/api/chats")
async def create_chat(
    chat: ChatCreate,
    clerk_id: str = Depends(get_current_user)
):
    try:
        result = supabase.table("chats").insert({
            "title": chat.title,
            "project_id": chat.project_id,
            "clerk_id": clerk_id
        }).execute()

        print("Chat creation result:", result)

        return {
            "message": "Chat created successfully",
            "data": result.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")
    
@router.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        deleted_result = supabase.table("chats").delete().eq("id", chat_id).eq("clerk_id", clerk_id).execute()
        if not deleted_result.data:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        return {
            "message": "Chat deleted successfully",
            "data": deleted_result.data[0]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")

@router.get("/api/chats/{chat_id}")
async def get_chat(
    chat_id: str,
    clerk_id: str = Depends(get_current_user)
):
    try:
        # Get the chat and verify it belongs to the user AND has a project_id
        result = supabase.table('chats').select('*').eq('id', chat_id).eq('clerk_id', clerk_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
        
        chat = result.data[0]
        
        # Get messages for this chat
        messages_result = supabase.table('messages').select('*').eq('chat_id', chat_id).order('created_at', desc=False).execute()
        
        # Add messages to chat object
        chat['messages'] = messages_result.data or []
        
        return {
            "message": "Chat retrieved successfully",
            "data": chat
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat: {str(e)}")
def load_project_settings(project_id: str) -> dict:
    """Load project settings from database"""
    print(f"⚙️ Fetching project settings...")
    settings_result = supabase.table('project_settings').select('*').eq('project_id', project_id).execute()
    
    if not settings_result.data:
        raise HTTPException(status_code=404, detail="Project settings not found")
    
    settings = settings_result.data[0]
    print(f"✅ Settings retrieved")
    return settings

def get_document_ids(project_id: str) -> List[str]:
    """Get all document IDs for a project"""
    print(f"📄 Fetching project documents...")
    documents_result = supabase.table('project_documents').select('id').eq('project_id', project_id).execute()
    
    document_ids = [doc['id'] for doc in documents_result.data]
    print(f"✅ Found {len(document_ids)} documents")
    return document_ids

def rrf_rank_and_fuse(search_results_lists: List[List[Dict]], weights: List[float] = None, k:int = 60)-> List[Dict]:
    """RRF (Reciprocal Rank Fusion) ranking"""

    if not search_results_lists or not any(search_results_lists):
        return []
    
    if weights is None:
        weights = [1.0 / len(search_results_lists)] * len(search_results_lists)

    chunk_scores = {}
    all_chunks = {}

    for search_idx, results in enumerate(search_results_lists):
        weight = weights[search_idx]

        for rank, chunk in enumerate[Dict](results):
            chunk_id = chunk.get('id')
            if not chunk_id:
                continue

            rrf_score = weight * (1.0 / (k + rank + 1))

            if chunk_id in chunk_scores:
                chunk_scores[chunk_id] += rrf_score

            else:
                chunk_scores[chunk_id] = rrf_score
                all_chunks[chunk_id] = chunk

    sorted_chunk_ids = sorted(chunk_scores.keys(), key=lambda cid: chunk_scores[cid], reverse=True) 
    return [all_chunks[chunk_id] for chunk_id in sorted_chunk_ids]

def vector_search(query: str, document_ids: List[str], settings: dict) -> List[Dict]:
    """Execute vector search"""

    query_embedding = embeddings_model.embed_query(query)
    
    result = supabase.rpc('vector_search_document_chunks', {
        'query_embedding': query_embedding,
        'filter_document_ids': document_ids,
        'match_threshold': settings['similarity_threshold'],
        'chunk_per_search': settings['chunk_per_search']
    }).execute()

    return result.data if result.data else []

def keyword_search(query: str, document_ids: List[str], settings: dict) -> List[Dict]:
    """Exexute keyword search"""
    result = supabase.rpc('keyword_search_document_chunks', {
        'query_text': query,
        'filter_document_ids': document_ids,
        'chunk_per_search': settings['chunk_per_search']
    }).execute()

    return result.data if result.data else []

def hybrid_search(query: str, document_ids: List[str], settings: dict) -> List[Dict]:
    """Execute hybrid search by combining vector and keyword results"""
    # Get results from both search methods
    vector_results = vector_search(query, document_ids, settings)
    keyword_results = keyword_search(query, document_ids, settings)

    print(f"📈 Vector search returned: {len(vector_results)} chunks")
    print(f"📈 Keyword search returned: {len(keyword_results)} chunks")
    
    # Combine using RRF with configured weights
    return rrf_rank_and_fuse(
        [vector_results, keyword_results], 
        [settings['vector_weight'], settings['keyword_weight']]
    )

def fetch_images_from_s3(image_keys: List[str]) -> List[str]:
    """Fetch images from S3 and return as base64 strings"""
    images_base64 = []
    for s3_key in image_keys:
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            image_bytes = response['Body'].read()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            images_base64.append(image_b64)
            print(f"✅ Fetched image from S3: {s3_key}")
        except Exception as e:
            print(f"⚠️ Failed to fetch image {s3_key}: {e}")
    return images_base64

class QueryVariations(BaseModel):
    queries: List[str]

def generate_query_variations(original_query: str, num_queries: int = 3) -> List[str]:
    """Generate query variations using LLM"""
    system_prompt = f"""Generate {num_queries-1} alternative ways to phrase this question for document search. Use different keywords and synonyms while maintaining the same intent. Return exactly {num_queries-1} variations."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Original query: {original_query}")
        ]
        
        structured_llm = llm.with_structured_output(QueryVariations)
        result = structured_llm.invoke(messages)
        
        return [original_query] + result.queries[:num_queries-1]
    except Exception:
        return [original_query]
    
def build_context(chunks: List[Dict]) -> Tuple[List[str], List[str], List[str], List[Dict]]:
    """Returns:
            Tuple of (texts, images, tables, citations)"""

    if not chunks:
        return [], [], [], []

    texts = []
    images = []
    tables = []
    citations = []

    # Batch fetch all filenames in One query
    doc_ids = [chunk['document_id'] for chunk in chunks if chunk.get('document_id')] 
    unique_doc_id: List[str] = list[str](set[str](doc_ids))   

    filename_map = {}

    if unique_doc_id:
        result = supabase.table('project_documents')\
            .select('id, filename')\
            .in_('id', unique_doc_id)\
            .execute()
        filename_map = {doc['id']: doc['filename'] for doc in result.data}

    # Process each chunk and categorize content
    for chunk in chunks:
        original_content = chunk.get('original_content', {})

        # Extract content from chunk
        chunk_text = original_content.get('text', '')
        chunk_image_keys = original_content.get('image_keys', [])  # ← S3 keys
        chunk_tables = original_content.get('tables', [])

        # collect content
        if chunk_text:
            texts.append(chunk_text)

        # if chunk_image_keys:
        #     print(f"🖼️ Fetching {len(chunk_image_keys)} images from S3...")
        #     chunk_images_b64 = fetch_images_from_s3(chunk_image_keys)
        #     images.extend(chunk_images_b64)
        if chunk_image_keys and len(images) < 6:
            remaining = 6 - len(images)
            print(f"🖼️ Fetching {min(len(chunk_image_keys), remaining)} images from S3...")
            chunk_images_b64 = fetch_images_from_s3(chunk_image_keys[:remaining])
            images.extend(chunk_images_b64)

        tables.extend(chunk_tables)

        # add citation for every chunk

        doc_id = chunk.get('document_id')
        if doc_id:
            citations.append({
                "chunk_id": chunk.get('id'),
                "document_id": doc_id,
                "filename": filename_map.get(doc_id, "Unknown Document"),
                "page": chunk.get('page_number', 'unknown')
            })

    return texts, images, tables, citations

def prepare_prompt_and_invoke_llm(
    user_query: str,
    texts: List[str],
    images: List[str],
    tables: List[str]
) -> str:
    """
    Builds system prompt with context and invokes LLM with multi-modal support
    
    Args:
        user_query: The user's question
        texts: List of text chunks from documents
        images: List of base64-encoded images
        tables: List of HTML table strings
    
    Returns:
        AI response string
    """
    # Build system prompt parts
    prompt_parts = []
    
    # Main instruction
    prompt_parts.append(
        "You are a helpful AI assistant that answers questions based solely on the provided context. "
        "Your task is to provide accurate, detailed answers using ONLY the information available in the context below.\n\n"
        "IMPORTANT RULES:\n"
        "- Only answer based on the provided context (texts, tables, and images)\n"
        "- If the answer cannot be found in the context, respond with: 'I don't have enough information in the provided context to answer that question.'\n"
        "- Do not use external knowledge or make assumptions beyond what's explicitly stated\n"
        "- When referencing information, be specific and cite relevant parts of the context\n"
        "- Synthesize information from texts, tables, and images to provide comprehensive answers\n\n"
    )
    # Add text context
    if texts:
        prompt_parts.append("=" * 80)
        prompt_parts.append("CONTEXT DOCUMENTS")
        prompt_parts.append("=" * 80 + "\n")

        for i, text in enumerate(texts, 1):
            prompt_parts.append(f"--- Document Chunk {i} ---")
            prompt_parts.append(text.strip())
            prompt_parts.append("")

    if tables:
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("RELATED TABLES")
        prompt_parts.append("=" * 80)
        prompt_parts.append(
            "The following tables contain structured data that may be relevant to your answer. "
            "Analyze the table contents carefully.\n"
        )
        
        for i, table_html in enumerate(tables, 1):
            prompt_parts.append(f"--- Table {i} ---")
            prompt_parts.append(str(table_html))
            prompt_parts.append("")
    
    # Reference images if present
    if images:
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("RELATED IMAGES")
        prompt_parts.append("=" * 80)
        prompt_parts.append(
            f"{len(images)} image(s) will be provided alongside the user's question. "
            "These images may contain diagrams, charts, figures, formulas, or other visual information. "
            "Carefully analyze the visual content when formulating your response. "
            "The images are part of the retrieved context and should be used to answer the question.\n"
        )
    
    # Final instruction
    prompt_parts.append("=" * 80)
    prompt_parts.append(
        "Based on all the context provided above (documents, tables, and images), "
        "please answer the user's question accurately and comprehensively."
    )
    prompt_parts.append("=" * 80)
    
    system_prompt = "\n".join(prompt_parts)

    # build messagesfor LLM
    messages = [SystemMessage(content = system_prompt)]

    # crate human message with user_quey and images
    if images:
        # multi modal message : text + image

        content_parts = [{"type": "text", "text" : user_query}]
        # add each image to the content parts
        for img_base64 in images:
            # Clean base64 string if it has data URI prefix
            if img_base64.startswith('data:image'):
                img_base64 = img_base64.split(',', 1)[1]
            
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
            })

        messages.append(HumanMessage(content = content_parts))

    else:
        messages.append(HumanMessage(content = user_query))

    # invoke LLM and return response

    print(f"Invoking LLM with {len(messages)} messages ({len(texts)} text chunks, {len(images)} images, {len(tables)} tables...)")

    response = llm.invoke(messages)

    return response.content

def validate_context(texts: List[str], images: List[str], tables: List[str], citations: List[Dict]) -> None:
    """Validate and print context data in a readable format"""
    print("\n" + "="*80)
    print("📦 CONTEXT VALIDATION")
    print("="*80)
    
    # Texts - SHOW FULL TEXT
    print(f"\n📝 TEXTS: {len(texts)} chunks")
    for i, text in enumerate(texts, 1):
        print(f"\n{'='*80}")
        print(f"CHUNK [{i}] - {len(text)} characters")
        print(f"{'='*80}")
        print(text)  # ✅ Full text, no truncation
        print(f"{'='*80}\n")
    
    # Images
    print(f"\n🖼️  IMAGES: {len(images)}")
    for i, img in enumerate(images, 1):
        img_preview = str(img)[:60] + ('...' if len(str(img)) > 60 else '')
        print(f"  [{i}] {img_preview}")
    
    # Tables
    print(f"\n📊 TABLES: {len(tables)}")
    for i, table in enumerate(tables, 1):
        if isinstance(table, dict):
            rows = len(table.get('rows', []))
            cols = len(table.get('headers', []))
            print(f"  [{i}] {rows} rows × {cols} cols")
        else:
            print(f"  [{i}] Type: {type(table).__name__}")
    
    # Citations
    print(f"\n📚 CITATIONS: {len(citations)}")
    for i, cite in enumerate(citations, 1):
        chunk_id = cite['chunk_id'][:8] if cite.get('chunk_id') else 'N/A'
        print(f"  [{i}] {cite['filename']} (pg.{cite['page']}) | chunk: {chunk_id}...")
    
    # Summary
    total_chars = sum(len(text) for text in texts)
    print(f"\n{'='*80}")
    print(f"✅ Total: {len(texts)} texts ({total_chars:,} chars), {len(images)} images, {len(tables)} tables, {len(citations)} citations")
    print("="*80 + "\n")

class SendMessageRequest(BaseModel):
    content: str

@router.post("/api/projects/{project_id}/chats/{chat_id}/messages")
async def send_message(
    chat_id: str,
    request: SendMessageRequest,
    project_id: str,
    clerk_id: str = Depends(get_current_user)
):
    """
        User message → LLM → AI response
    """
    try:
        message = request.content
        
        print(f"💬 New message: {message[:50]}...")
        
        # 1. Save user message
        print(f"💾 Saving user message...")
        user_message_result = supabase.table('messages').insert({
            "chat_id": chat_id,
            "content": message,
            "role": "user",
            "clerk_id": clerk_id
        }).execute()
        
        user_message = user_message_result.data[0]
        print(f"✅ User message saved: {user_message['id']}")
        
        # 2. Load project settings
        # We need settings to know: chunk size, similarity threshold, etc.
        settings = load_project_settings(project_id)
        
        # 3. Get document IDs for this project
        # This narrows our search scope to only documents uploaded to this specific project
        document_ids = get_document_ids(project_id)
        strategy  = settings['rag_strategy']
        print(f"\n RAG Strategy: {strategy.upper()}")
        
        # 4. Generate query embedding
        # Convert the user's text question into a vector so we can perform similarity search
        # 5. Perform vector search using the RPC function

        if strategy == 'basic':
            chunks = vector_search(message,document_ids, settings)
            print(f"✅ Retrieved {len(chunks)} relevant chunks from vector search")

        elif strategy == 'hybrid':
            print("Execting: Hybrid Search (Vector + Keyword)")
            chunks = hybrid_search(message,document_ids, settings)
            print(f"✅ Hybrid search retuned {len(chunks)} relevant chunks")

        elif strategy == "multi-query-vector":
            print(f"Executing : Multi-Query Vector Search ({settings['number_of_queries']} queries)")
            queries = generate_query_variations(message, settings['number_of_queries'])
            print(f"Generated Queries: {queries}")

            all_results = []

            for i, q in enumerate(queries):
                results = vector_search(q, document_ids, settings)
                print(f"Query {i+1} '{q}' returned: {len(results)} chunk")
                all_results.append(results)

            chunks = rrf_rank_and_fuse(all_results)
            print(f"RRF fusion returned: {len(chunks)} chunks")        
        # # Search through the chunks to find the most relevant chunks for answering the question
        # chunks = vector_search(message,document_ids, settings)
        # print(f"✅ Retrieved {len(chunks)} relevant chunks from vector search")
        elif strategy == 'multi-query-hybrid':
            print(f"📈 Executing: Multi-Query Hybrid Search ({settings['number_of_queries']} queries, Vector + Keyword)")
            queries = generate_query_variations(message, settings['number_of_queries'])
            print(f"🔄 Generated queries: {queries}")
            
            # Stage 1: Per-query hybrid fusion
            all_hybrid_results = []
            for i, q in enumerate(queries):
                print(f"\n  Query {i+1}: '{q}'")
                
                # Use the existing hybrid_search function which handles weights
                hybrid_results = hybrid_search(q, document_ids, settings)
                
                print(f"Hybrid fusion returned: {len(hybrid_results)} chunks")
                
                all_hybrid_results.append(hybrid_results)
            
            # Stage 2: Cross-query fusion (equal weights across queries by default)
            print(f"\nFinal RRF fusion across {len(all_hybrid_results)} queries")
            chunks = rrf_rank_and_fuse(all_hybrid_results)
            print(f"📊 Final result: {len(chunks)} chunks")
        

        # 5. Trim to final context size
        chunks = chunks[:settings['final_context_size']]
        print(f"Trimmed to final context size: {len(chunks)} chunks")

        
        
        # 6. Build context from retrieved chunks
        # Format the retrieved chunks into a structured context with citations
        texts, images, tables, citations = build_context(chunks)
        validate_context(texts, images, tables, citations)

        
        # 7. Build system prompt with injected context
        # Add the retrieved document context to the system prompt so the LLM can answer based on the documents
            # 8. Call LLM & get response
        # The LLM now has access to relevant document chunks and can provide informed answers
        ai_response = prepare_prompt_and_invoke_llm(
            user_query = message,
            texts = texts,
            images = images,
            tables = tables
        )

        print(f"LLM response ({len(ai_response)} characters)")
        
    
        
        # 9. Save AI message with citations to database
        # Store the AI's response along with citations

        
     
        print(f"💾 Saving AI message...")
        ai_message_result = supabase.table('messages').insert({
            "chat_id": chat_id,
            "content": ai_response,
            "role": "assistant",
            "clerk_id": clerk_id,
            "citations": citations
        }).execute()
        
        ai_message = ai_message_result.data[0]
        print(f"✅ AI message saved: {ai_message['id']}")
        
        # 4. Return data
        return {
            "message": "Messages sent successfully",
            "data": {
                "userMessage": user_message,
                "aiMessage": ai_message
            }
        }
        
    except Exception as e:
        print(f"❌ Error in send_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))