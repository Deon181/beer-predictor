-- Profiles: 1:1 with auth.users, holds display_name only.
CREATE TABLE public.profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 50),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User beers: one row per (user, catalog beer slug).
CREATE TABLE public.user_beers (
  id        BIGSERIAL PRIMARY KEY,
  user_id   UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  beer_id   TEXT NOT NULL,
  rating    NUMERIC(2,1) NOT NULL
             CHECK (rating IN (0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0)),
  rated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, beer_id)
);
CREATE INDEX user_beers_user_idx ON public.user_beers (user_id);

-- Trigger: mirror new auth users into public.profiles.
-- Lives in private schema with empty search_path per Supabase security guide.
CREATE SCHEMA IF NOT EXISTS private;

CREATE FUNCTION private.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name)
  VALUES (NEW.id,
          COALESCE(NEW.raw_user_meta_data->>'display_name',
                   split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION private.handle_new_user();

-- Enable RLS.
ALTER TABLE public.profiles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_beers ENABLE ROW LEVEL SECURITY;

-- profiles policies.
CREATE POLICY profiles_select_own
  ON public.profiles FOR SELECT TO authenticated
  USING (id = auth.uid());

CREATE POLICY profiles_update_own
  ON public.profiles FOR UPDATE TO authenticated
  USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- user_beers policies.
CREATE POLICY user_beers_select_own
  ON public.user_beers FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY user_beers_insert_own
  ON public.user_beers FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY user_beers_update_own
  ON public.user_beers FOR UPDATE TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY user_beers_delete_own
  ON public.user_beers FOR DELETE TO authenticated
  USING (user_id = auth.uid());

-- Grants. anon gets nothing on these tables.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles    TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_beers  TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.user_beers_id_seq   TO authenticated;
