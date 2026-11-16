-- Prefix the beer predictor's tables with beer_.
--
-- This Supabase project (renamed "other") also holds the recipe app's recipe_*
-- tables and lunara's lunara_* tables, so each app's tables carry its name.
-- Policies, grants, indexes and constraints stay attached through a rename. The
-- sign-up trigger's function holds the table name as text, so it is re-created.
-- Views under the old names keep a not-yet-redeployed app working (security_invoker,
-- so RLS still applies as the caller); drop them once the beer_ code is live.

alter table public.profiles   rename to beer_profiles;
alter table public.user_beers rename to beer_user_beers;

CREATE OR REPLACE FUNCTION private.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
BEGIN
  INSERT INTO public.beer_profiles (id, display_name)
  VALUES (NEW.id,
          COALESCE(NEW.raw_user_meta_data->>'display_name',
                   split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$function$;

create view public.profiles with (security_invoker = on) as select * from public.beer_profiles;
create view public.user_beers with (security_invoker = on) as select * from public.beer_user_beers;
revoke all on public.profiles, public.user_beers from public, anon;
grant select, insert, update, delete on public.profiles, public.user_beers to authenticated, service_role;

notify pgrst, 'reload schema';
