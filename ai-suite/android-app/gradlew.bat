@echo off
setlocal
set VERSION=9.3.1
set SHA256=b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06
if "%GRADLE_USER_HOME%"=="" (
  set BASE=%USERPROFILE%\.gradle\byblos-bootstrap
) else (
  set BASE=%GRADLE_USER_HOME%\byblos-bootstrap
)
set INSTALL=%BASE%\gradle-%VERSION%
set ZIP=%BASE%\gradle-%VERSION%-bin.zip
set URL=https://services.gradle.org/distributions/gradle-%VERSION%-bin.zip

if not exist "%INSTALL%\bin\gradle.bat" (
  if not exist "%BASE%" mkdir "%BASE%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "if (-not (Test-Path '%ZIP%')) { Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' };" ^
    "$hash=(Get-FileHash '%ZIP%' -Algorithm SHA256).Hash.ToLower();" ^
    "if ($hash -ne '%SHA256%') { throw 'Gradle SHA-256 verification failed' };" ^
    "if (Test-Path '%INSTALL%') { Remove-Item '%INSTALL%' -Recurse -Force };" ^
    "Expand-Archive -Path '%ZIP%' -DestinationPath '%BASE%' -Force"
  if errorlevel 1 exit /b 1
)

call "%INSTALL%\bin\gradle.bat" %*
endlocal
