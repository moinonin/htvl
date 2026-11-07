"""Project compilation tests (files, assets, CGI output)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from htvl.project import compile_project


@pytest.fixture
def project(tmp_path):
    (tmp_path / "index.htvl").write_text(
        "$DOCTYPE_htvl\n$htvl\n$head\n$_head\n$body\n"
        "  $(h 1 '' '' 'Hi' '')\n$_body\n$_htvl\n",
        encoding="utf-8",
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "style.css").write_text(
        "body{}\n", encoding="utf-8"
    )
    return tmp_path


def test_compile_project_writes_public_html_and_assets(project):
    result = compile_project(project)
    html = (project / "public" / "index.html").read_text(encoding="utf-8")
    assert "<h1" in html and "Hi" in html
    assert (project / "public" / "assets" / "style.css").exists()
    assert len(result.outputs) == 1


def test_compile_project_custom_out_dir(project):
    compile_project(project, out_dir="build")
    assert (project / "build" / "index.html").exists()


def test_compile_project_fails_without_sources(tmp_path):
    with pytest.raises(Exception) as excinfo:
        compile_project(tmp_path)
    assert "no .htvl or .cal files" in str(excinfo.value)


def test_cal_files_become_executable_cgi_scripts(tmp_path):
    (tmp_path / "hello.cal").write_text(
        "$DOCTYPE_htvl\n$htvl\n  $(h 1 '' '' 'CGI' '')\n$_htvl\n",
        encoding="utf-8",
    )
    result = compile_project(tmp_path)
    script = tmp_path / "cal" / "hello"
    assert script.exists()
    assert script in result.outputs
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "<h1" in text
    assert os.access(script, os.X_OK)
