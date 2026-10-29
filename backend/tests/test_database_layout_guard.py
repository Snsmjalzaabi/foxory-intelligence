"""Execute the trusted entrypoint guard against fictional files, never a database."""
from pathlib import Path
import os
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
GUARD=ROOT/'deployment/postgres/entrypoint.sh'


@pytest.mark.parametrize('marker',[None,'different-layout','symlink'])
@pytest.mark.parametrize('command',['postgres','-c'])
def test_legacy_directory_refused_without_downstream_execution_or_changes(tmp_path,marker,command):
    data=tmp_path/'data';data.mkdir()
    (data/'PG_VERSION').write_text('17\n')
    if marker=='symlink':
        other=tmp_path/'outside';other.write_text('foxory-postgres17-alpine-v1\n')
        (data/'.foxory-layout').symlink_to(other)
    elif marker:(data/'.foxory-layout').write_text(marker)
    before={p.name:(p.lstat().st_mode,p.lstat().st_mtime_ns,p.read_bytes()) for p in data.iterdir()}
    result=subprocess.run(['bash',str(GUARD),command],env={**os.environ,'PGDATA':str(data)},capture_output=True,text=True,timeout=5)
    assert result.returncode==78 and 'FOXORY_DATABASE_LAYOUT_MISMATCH' in result.stderr
    assert {p.name:(p.lstat().st_mode,p.lstat().st_mtime_ns,p.read_bytes()) for p in data.iterdir()}==before


@pytest.mark.parametrize('initialized',[False,True])
def test_only_new_or_matching_cluster_reaches_upstream(tmp_path,initialized):
    data=tmp_path/'data';data.mkdir()
    if initialized:
        (data/'PG_VERSION').write_text('17\n')
        (data/'.foxory-layout').write_text('foxory-postgres17-alpine-v1\n')
    upstream=tmp_path/'upstream'
    upstream.write_text('#!/bin/bash\nprintf "UPSTREAM_REACHED\\n"\n')
    upstream.chmod(0o700)
    # A controlled stand-in exercises only the trust guard; OCI integration
    # separately proves actual initdb/restart/logical restore behavior.
    source=GUARD.read_text().replace('/usr/local/bin/docker-entrypoint.sh',str(upstream))
    result=subprocess.run(['bash','-c',source,'fixture','postgres'],env={**os.environ,'PGDATA':str(data)},capture_output=True,text=True,timeout=5)
    assert result.returncode==0 and result.stdout=='UPSTREAM_REACHED\n'


@pytest.mark.parametrize('version',[None,'','18\n'])
def test_partial_or_wrong_major_cluster_is_not_initialized_in_place(tmp_path,version):
    data=tmp_path/'data';data.mkdir()
    (data/'.foxory-layout').write_text('foxory-postgres17-alpine-v1\n')
    if version is not None:(data/'PG_VERSION').write_text(version)
    result=subprocess.run(['bash',str(GUARD),'postgres'],env={**os.environ,'PGDATA':str(data)},capture_output=True,text=True,timeout=5)
    assert result.returncode==78 and 'FOXORY_DATABASE_LAYOUT_MISMATCH' in result.stderr
