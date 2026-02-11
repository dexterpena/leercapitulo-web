-- Run this in the Supabase SQL Editor to set up the database schema.

-- Library: user's saved manga
create table if not exists library (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  manga_url text not null,
  manga_title text not null,
  cover_url text,
  status text not null default 'reading',
  current_chapter float not null default 0,
  anilist_media_id int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, manga_url)
);

-- Anilist tokens: store user's Anilist OAuth tokens
create table if not exists anilist_tokens (
  user_id uuid primary key references auth.users(id) on delete cascade,
  access_token text not null,
  expires_at timestamptz,
  anilist_user_id int,
  anilist_username text
);

-- Enable Row Level Security
alter table library enable row level security;
alter table anilist_tokens enable row level security;

-- RLS policies: users can only access their own data
create policy "Users can view own library" on library
  for select using (auth.uid() = user_id);

create policy "Users can insert own library" on library
  for insert with check (auth.uid() = user_id);

create policy "Users can update own library" on library
  for update using (auth.uid() = user_id);

create policy "Users can delete own library" on library
  for delete using (auth.uid() = user_id);

create policy "Users can view own anilist tokens" on anilist_tokens
  for select using (auth.uid() = user_id);

create policy "Users can insert own anilist tokens" on anilist_tokens
  for insert with check (auth.uid() = user_id);

create policy "Users can update own anilist tokens" on anilist_tokens
  for update using (auth.uid() = user_id);

create policy "Users can delete own anilist tokens" on anilist_tokens
  for delete using (auth.uid() = user_id);
