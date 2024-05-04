:: build latest frontend
cd frontend
call npm run build:standalone
cd ..

:: copy files
mkdir electron\frontend
xcopy /s/e frontend\dist electron\frontend\dist\

pyarmor cfg data_files=*
pyarmor cfg nts=local
pyarmor gen -O electron -e 2024-11-01 --recursive backend
move electron\pyarmor_runtime_004553 electron\backend\src\

mkdir electron\submodules
pyarmor gen -O electron\submodules -e 2024-11-01 --recursive submodules\topicsync
pyarmor gen -O electron\submodules -e 2024-11-01 --recursive submodules\objectsync
xcopy /s/e electron\submodules\pyarmor_runtime_004553 electron\submodules\topicsync\src\pyarmor_runtime_004553\
move electron\submodules\pyarmor_runtime_004553 electron\submodules\objectsync\src\


pyarmor gen -O electron -e 2024-11-01 --recursive extensions
move electron\pyarmor_runtime_004553 electron\extensions\

pyarmor gen -O electron  -e 2024-11-01 --recursive entry\standalone
cd electron
rename standalone entry
cd ..
move electron\pyarmor_runtime_004553 electron\entry\

cd electron
call npm run test 
cd ..

rmdir /s/q electron\frontend
rmdir /s/q electron\backend 
rmdir /s/q electron\submodules
rmdir /s/q electron\extensions
rmdir /s/q electron\entry