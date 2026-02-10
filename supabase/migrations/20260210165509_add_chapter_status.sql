CREATE TABLE IF NOT EXISTS chapter_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  manga_url text NOT NULL,
  chapter_url text NOT NULL,
  is_read boolean NOT NULL DEFAULT false,
  is_bookmarked boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, chapter_url)
);

ALTER TABLE chapter_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own chapter status" ON chapter_status
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chapter status" ON chapter_status
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chapter status" ON chapter_status
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own chapter status" ON chapter_status
  FOR DELETE USING (auth.uid() = user_id);
