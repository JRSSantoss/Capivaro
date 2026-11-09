@echo off
setlocal
title Capivara - preparando...
cd /d "%~dp0"

rem ============================================================
rem  Inicia a Capivara. Na primeira vez instala tudo sozinho:
rem   1) Python (se nao tiver)   2) PySide6   3) abre a capivara
rem ============================================================

set "PYCMD="
set "PYARG="

call :achar_python
if defined PYCMD goto :tem_python

echo.
echo  Python nao encontrado. Instalando automaticamente...
echo  Pode levar alguns minutos e so acontece uma vez.
echo.

where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
)
call :achar_python
if defined PYCMD goto :tem_python

echo  Baixando o instalador do Python direto do python.org...
set "INSTALADOR=%TEMP%\python-capivara-setup.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%INSTALADOR%'"
if exist "%INSTALADOR%" (
    "%INSTALADOR%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
)
call :achar_python
if defined PYCMD goto :tem_python

echo.
echo  Nao consegui instalar o Python automaticamente.
echo  Vou abrir o site: baixe, instale e marque Add Python to PATH,
echo  e depois abra este arquivo de novo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:tem_python
%PYCMD% %PYARG% -c "import PySide6, numpy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Instalando a capivara pela primeira vez...
    echo  Leva 1 a 2 minutos, so desta vez. Nao feche esta janela.
    echo.
    %PYCMD% %PYARG% -m pip install --disable-pip-version-check PySide6 numpy
    if errorlevel 1 (
        echo.
        echo  Falhou a instalacao. Verifique sua internet e tente de novo.
        pause
        exit /b 1
    )
)

rem descobre o pythonw.exe (roda sem janela preta)
set "PYW="
for /f "usebackq delims=" %%i in (`%PYCMD% %PYARG% -c "import sys,os;d=os.path.dirname(sys.executable);print(os.path.join(d,'pythonw.exe'))"`) do set "PYW=%%i"

if not defined PYW goto :sem_pythonw
if not exist "%PYW%" goto :sem_pythonw
start "" "%PYW%" "%~dp0capivara.pyw"
exit /b 0

:sem_pythonw
start "" %PYCMD% %PYARG% "%~dp0capivara.pyw"
exit /b 0

rem ------------------------------------------------------------
:achar_python
set "PYCMD="
set "PYARG="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py"
    set "PYARG=-3"
    goto :eof
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python"
    goto :eof
)
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
) do (
    if exist %%P if not defined PYCMD set "PYCMD=%%P"
)
goto :eof
