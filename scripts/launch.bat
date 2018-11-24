timeout /t 2 /nobreak > NUL
robocopy /E /MOVE "%1" %2

start LalkaChat.exe