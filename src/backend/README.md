--Backend
1. .venv\Activate\Scripts
2. docker ps -a
3. docker compose up -d
4. docker start convo_history_db
5. python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000

--Frontend
1. npm install
2. npm start