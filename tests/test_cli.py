"""CLI tests."""

from __future__ import annotations

import pytest

from htvl.cli import main


def test_compile_command(tmp_path, capsys):
    (tmp_path / "index.htvl").write_text(
        "$(h 1 '' '' 'Hi' '')\n", encoding="utf-8"
    )
    code = main(["compile", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "public" / "index.html").exists()
    out = capsys.readouterr().out
    assert "compiled" in out


def test_compile_reports_missing_directory(capsys):
    code = main(["compile", "/definitely/not/here"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_check_writes_html_to_stdout(tmp_path, capsys):
    path = tmp_path / "x.htvl"
    path.write_text("$br\n", encoding="utf-8")
    code = main(["check", str(path)])
    assert code == 0
    assert capsys.readouterr().out == "<br>\n\n"


def test_new_scaffolds_a_project(tmp_path, capsys):
    code = main(["new", str(tmp_path / "site")])
    assert code == 0
    project = tmp_path / "site"
    assert (project / "index.htvl").exists()
    assert (project / "templates" / "headtags.htvl").exists()
    # The scaffold must compile.
    assert main(["compile", str(project)]) == 0
    assert (project / "public" / "index.html").exists()


def test_list_command(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "$(h level class id content style)" in out
    assert "$head -> <head>" in out


def test_version_flag_exits_with_version():
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
