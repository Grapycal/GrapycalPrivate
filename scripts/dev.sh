cd frontend && npm run build:standalone && cd .. &&\

python entry/run.py --backend-path "backend/src" --frontend-path "frontend/dist"