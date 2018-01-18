@echo off
cmd /c "cd /d %~dp0\env\Scripts & activate & cd /d  %~dp0\ & py parser.py"
