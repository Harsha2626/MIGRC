@echo off
cd /d "%~dp0"

rem Best-effort: make sure a local OpenCode server is up for the AI policy-evaluation
rem feature's fallback models (DeepSeek / free tier) - see scripts/opencode_local_session.py.
rem Not required for the active Cline-direct model, but keeps the fallback path ready.
rem Failure here is non-fatal; app.py's evaluation feature fails open regardless.
venv-migrc\Scripts\python.exe scripts\opencode_local_session.py

venv-migrc\Scripts\python.exe app.py
pause
