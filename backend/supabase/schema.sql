-- Reference schema for the tables the backend reads/writes directly via
-- supabase_client (app/db/supabase.py). Run this once against the project's
-- Postgres database (SQL editor in the Supabase dashboard, or `psql`).
-- Phase 8: app/api/v1/endpoints/research.py inserts a row on task start and
-- app/agents/nodes/reporter.py updates it + inserts into SavedMaterials on completion.

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
