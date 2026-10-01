-- Step 1: storage for document chunks + vector search.
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run.

create extension if not exists vector;

create table if not exists chunks (
  id          bigserial primary key,
  doc_id      uuid        not null,
  page        int         not null,
  chunk_index int         not null,
  content     text        not null,
  embedding   vector(768) not null,
  created_at  timestamptz not null default now()
);

-- HNSW index for fast cosine search (works up to 2000 dims, hence 768).
create index if not exists chunks_embedding_hnsw
  on chunks using hnsw (embedding vector_cosine_ops);

-- Every query is scoped to one document.
create index if not exists chunks_doc_id_idx on chunks (doc_id);

-- Lock the table: no policies = the public (anon) key can't read or write.
-- The backend uses the secret key, which bypasses RLS.
alter table chunks enable row level security;

-- Top-k chunks of one document, most similar first.
-- score = cosine similarity (1 = identical direction, 0 = unrelated).
create or replace function match_chunks(
  query_embedding vector(768),
  p_doc_id        uuid,
  match_count     int default 5
)
returns table (id bigint, page int, chunk_index int, content text, score float)
language sql stable
as $$
  select c.id, c.page, c.chunk_index, c.content,
         1 - (c.embedding <=> query_embedding) as score
  from chunks c
  where c.doc_id = p_doc_id
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
