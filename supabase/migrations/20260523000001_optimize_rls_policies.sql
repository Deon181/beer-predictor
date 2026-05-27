-- Optimize RLS policies: wrap auth.uid() in (select auth.uid()) so it's
-- evaluated once per query instead of once per row.
-- See https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select

-- profiles
DROP POLICY profiles_select_own ON public.profiles;
DROP POLICY profiles_update_own ON public.profiles;

CREATE POLICY profiles_select_own
  ON public.profiles FOR SELECT TO authenticated
  USING (id = (select auth.uid()));

CREATE POLICY profiles_update_own
  ON public.profiles FOR UPDATE TO authenticated
  USING (id = (select auth.uid())) WITH CHECK (id = (select auth.uid()));

-- user_beers
DROP POLICY user_beers_select_own ON public.user_beers;
DROP POLICY user_beers_insert_own ON public.user_beers;
DROP POLICY user_beers_update_own ON public.user_beers;
DROP POLICY user_beers_delete_own ON public.user_beers;

CREATE POLICY user_beers_select_own
  ON public.user_beers FOR SELECT TO authenticated
  USING (user_id = (select auth.uid()));

CREATE POLICY user_beers_insert_own
  ON public.user_beers FOR INSERT TO authenticated
  WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY user_beers_update_own
  ON public.user_beers FOR UPDATE TO authenticated
  USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY user_beers_delete_own
  ON public.user_beers FOR DELETE TO authenticated
  USING (user_id = (select auth.uid()));
