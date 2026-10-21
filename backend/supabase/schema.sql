-- Schema for the tables used by AURA. Run once in the Supabase SQL editor.
--
-- RLS is enabled on every table. The frontend queries ResearchTasks and
-- chat_messages directly with the anon key, so per-user policies are what keep
-- one user from reading another user's rows. The backend uses the service role
-- key, which bypasses RLS, so the Celery reporter and FastAPI endpoints are
-- unaffected.

create table if not exists "ResearchTasks" (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    prompt text not null,
    status text not null default 'processing',
    result_json jsonb,
    created_at timestamptz not null default now()
);

create table if not exists "SavedMaterials" (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references "ResearchTasks"(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    composition text not null,
    predicted_capacity double precision,
    predicted_cost double precision,
    reasoning text,
    created_at timestamptz not null default now()
);

create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null,
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists research_tasks_user_id_idx on "ResearchTasks"(user_id);
create index if not exists saved_materials_task_id_idx on "SavedMaterials"(task_id);
create index if not exists chat_messages_user_id_idx on chat_messages(user_id);

alter table "ResearchTasks" enable row level security;
alter table "SavedMaterials" enable row level security;
alter table chat_messages enable row level security;

drop policy if exists "research_tasks_select_own" on "ResearchTasks";
create policy "research_tasks_select_own" on "ResearchTasks"
    for select using (auth.uid() = user_id);

drop policy if exists "research_tasks_insert_own" on "ResearchTasks";
create policy "research_tasks_insert_own" on "ResearchTasks"
    for insert with check (auth.uid() = user_id);

drop policy if exists "saved_materials_select_own" on "SavedMaterials";
create policy "saved_materials_select_own" on "SavedMaterials"
    for select using (auth.uid() = user_id);

drop policy if exists "chat_messages_select_own" on chat_messages;
create policy "chat_messages_select_own" on chat_messages
    for select using (auth.uid() = user_id);

drop policy if exists "chat_messages_insert_own" on chat_messages;
create policy "chat_messages_insert_own" on chat_messages
    for insert with check (auth.uid() = user_id);

drop policy if exists "chat_messages_delete_own" on chat_messages;
create policy "chat_messages_delete_own" on chat_messages
    for delete using (auth.uid() = user_id);

-- Literature vectors (pgvector). Replaces the former local ChromaDB store.
-- Embeddings are all-MiniLM-L6-v2 (384 dimensions), computed by app/services/embeddings.py.
create extension if not exists vector with schema extensions;

create table if not exists literature_chunks (
    id text primary key,
    document text not null,
    embedding extensions.vector(384) not null,
    doi text,
    title_key text,
    graph_extracted boolean not null default false,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists literature_chunks_embedding_idx
    on literature_chunks using hnsw (embedding extensions.vector_cosine_ops);
create index if not exists literature_chunks_doi_idx on literature_chunks (doi);
create index if not exists literature_chunks_title_key_idx on literature_chunks (title_key);
create index if not exists literature_chunks_pending_idx
    on literature_chunks (created_at) where graph_extracted = false;

-- Only the backend (service role, which bypasses RLS) reads or writes these rows.
alter table literature_chunks enable row level security;

create or replace function match_literature_chunks(query_embedding text, match_count int default 5)
returns table (id text, document text, metadata jsonb, similarity double precision)
language sql stable
set search_path = public, extensions
as $$
    select c.id, c.document, c.metadata || jsonb_build_object('doi', c.doi) as metadata,
           1 - (c.embedding <=> query_embedding::extensions.vector(384)) as similarity
    from literature_chunks c
    order by c.embedding <=> query_embedding::extensions.vector(384)
    limit match_count;
$$;

-- Chat messages keep the mode used and, for answers, the sources that were cited.
alter table chat_messages add column if not exists metadata jsonb not null default '{}'::jsonb;
