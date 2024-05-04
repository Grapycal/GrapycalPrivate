# build latest frontend
cd frontend
npm run build:standalone
cd ..

# copy files
mkdir electron/frontend
cp -R frontend/dist electron/frontend/dist

pyarmor cfg data_files=*
pyarmor cfg nts=local

pyarmor gen -O electron -e 2024-11-01 --recursive backend
mv electron/pyarmor_runtime_004553 electron/backend/src/pyarmor_runtime_004553

mkdir electron/submodules
pyarmor gen -O electron/submodules -e 2024-11-01 --recursive submodules/topicsync
pyarmor gen -O electron/submodules -e 2024-11-01 --recursive submodules/objectsync
cp -R electron/submodules/pyarmor_runtime_004553 electron/submodules/topicsync/src/pyarmor_runtime_004553
mv electron/submodules/pyarmor_runtime_004553 electron/submodules/objectsync/src/pyarmor_runtime_004553

pyarmor gen -O electron -e 2024-11-01 --recursive extensions
mv electron/pyarmor_runtime_004553 electron/extensions/pyarmor_runtime_004553

pyarmor gen -O electron  -e 2024-11-01 --recursive entry/standalone
mv electron/standalone electron/entry
mv electron/pyarmor_runtime_004553 electron/entry/pyarmor_runtime_004553

cd electron
npm run test 

cd ..
rm -r electron/frontend
rm -r electron/backend 
rm -r electron/submodules
rm -r electron/extensions
rm -r electron/entry