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
