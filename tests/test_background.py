"""Agente de launchd para las alertas, sin tocar el sistema real."""

import plistlib

from radar.alerts import background


def test_plist_runs_the_command_periodically_and_keeps_the_data_dir():
    raw = background.plist_content(["/x/radar-engine", "--check-alerts"], "/datos", "/datos/a.log")
    d = plistlib.loads(raw)
    assert d["Label"] == "es.radarbolsa.alertas"
    assert d["ProgramArguments"] == ["/x/radar-engine", "--check-alerts"]
    assert d["StartInterval"] == 900 and d["RunAtLoad"] is False
    assert d["EnvironmentVariables"] == {"RADAR_DATA_DIR": "/datos"}
    assert "EnvironmentVariables" not in plistlib.loads(background.plist_content(["a"], None, "/l"))


def test_enable_and_disable_write_and_remove_the_file(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(background.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(background, "_launchctl", lambda *a: calls.append(a))
    assert not background.is_enabled()
    background.enable()
    assert background.is_enabled() and background.plist_path().parent.name == "LaunchAgents"
    assert calls[-1][0] == "bootstrap"
    background.disable()
    assert not background.is_enabled() and calls[-1][0] == "bootout"
