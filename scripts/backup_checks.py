"""Shared fixed recovery checks; never emit row contents or secrets."""
import json
TABLES=['records','messages','audit','users','workspaces','memberships','login_sessions']
COUNTS_SQL='SELECT json_build_object('+','.join("'"+t+"',(SELECT count(*) FROM "+t+')' for t in TABLES)+',\'migration\',(SELECT string_agg(version_num,\',\') FROM alembic_version))'
