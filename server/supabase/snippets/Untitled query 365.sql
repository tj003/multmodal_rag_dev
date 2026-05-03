DROP FUNCTION IF EXISTS vector_search_document_chunks(vector, uuid[], double precision, integer);

CREATE FUNCTION vector_search_document_chunks(
    query_embedding vector, 
    filter_document_ids uuid[], 
    match_threshold double precision DEFAULT 0.3, 
    chunk_per_search integer DEFAULT 20
)
RETURNS TABLE(
    id uuid, 
    document_id uuid, 
    content text, 
    chunk_index integer, 
    created_at timestamptz, 
    page_number integer, 
    char_count integer, 
    "type" jsonb,
    original_content jsonb, 
    embedding vector
)
LANGUAGE sql
AS $$
SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    dc.created_at,
    dc.page_number,
    dc.char_count,
    dc."type",
    dc.original_content,
    dc.embedding
FROM document_chunks dc
WHERE
    dc.document_id = ANY(filter_document_ids)
    AND dc.embedding IS NOT NULL
    AND dc.embedding <=> query_embedding < (1 - match_threshold)
ORDER BY 
    dc.embedding <=> query_embedding
LIMIT chunk_per_search;
$$;