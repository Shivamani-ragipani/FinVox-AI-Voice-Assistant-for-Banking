--Backend
1. .venv\Activate\Scripts
1. docker ps -a
2. docker start convo_history_db
3. python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000

--Frontend
1. npm start