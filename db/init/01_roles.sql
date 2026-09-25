-- Runs once on first start of the postgres container. The API connects only as commanders_ro (SELECT on every
-- schema); the jobs and alembic use the owner role. Grants on future tables are set so migrations need no re-grant.
\set ro_pw `echo "$POSTGRES_RO_PASSWORD"`
CREATE ROLE commanders_ro LOGIN PASSWORD :'ro_pw';
GRANT CONNECT ON DATABASE commanders TO commanders_ro;
DO $$
DECLARE s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['nfl', 'gm', 'ml', 'ops'] LOOP
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION commanders', s);
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO commanders_ro', s);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE commanders IN SCHEMA %I GRANT SELECT ON TABLES TO commanders_ro', s);
  END LOOP;
END $$;
