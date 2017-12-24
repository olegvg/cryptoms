create schema btc_private;
create schema btc_public;

grant all PRIVILEGES on SCHEMA btc_private TO pg_user;
grant all PRIVILEGES on SCHEMA btc_public TO pg_user;
