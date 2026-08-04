-- Roles. Runs once, as the superuser, when the container initializes the
-- database. Production runs the same statements from Terraform.
--
-- Two roles, and the important property of both is what they do NOT have:
-- `nobypassrls`, so the policies in the migrations are not optional for
-- either. There is no anonymous role at all — nothing but the server ever
-- connects, so the old "anon has zero grants" rule has nothing to grant to.
-- docs/techstack/backend.md -> "Isolation: RLS on a session variable"

create role migrator login password 'migrator' nosuperuser nocreatedb nobypassrls;
create role app_user login password 'app_user' nosuperuser nocreatedb nobypassrls;

grant connect on database ddesign to migrator, app_user;
grant usage on schema public to migrator, app_user;

-- DDL belongs to the migration role, and to nothing else. `public` is a role
-- every user is implicitly a member of, which is why this revoke is not
-- redundant with the grants above.
revoke create on schema public from public;
grant create on schema public to migrator;

-- app_user reads and writes what migrator creates, and creates nothing.
alter default privileges for role migrator in schema public
  grant select, insert, update, delete on tables to app_user;
alter default privileges for role migrator in schema public
  grant usage, select on sequences to app_user;
