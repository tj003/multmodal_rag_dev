DROP FUNCTION IF EXISTS keyword_search_document_chunks(text, uuid[], integer);

CREATE FUNCTION keyword_search_document_chunks(
    query_text text, 
    filter_document_ids uuid[], 
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
WITH query AS (
  SELECT websearch_to_tsquery('english', query_text) AS q
)
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
FROM document_chunks dc, query
WHERE
    dc.fts @@ query.q
    AND dc.document_id = ANY(filter_document_ids)
ORDER BY 
    ts_rank_cd(dc.fts, query.q) DESC
LIMIT chunk_per_search;
$$;