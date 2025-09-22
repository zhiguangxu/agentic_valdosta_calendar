---
title: AI Calendar
emoji: 📅
colorFrom: blue
colorTo: pink
sdk: docker
app_file: backend/main.py
pinned: false
---

# My Agentic Calendar App

This is a simple Hugging Face Space running on Docker.

To start the backend locally: 
    fromt root folder: 
        ```bash
        uv run uvicorn backend.main:app --reload --port 8000

To start the frontend locally:
    from the frontend folder: 
        ```bash
        npm start

To deploy to Hugging Face:
    ```bash
    cd frontend
    npm install --> only once 
    npm run build
    cp -r build/* ../backend/static/

    cd ..
    git add .
    git commit -m "Deploy to HF"
    git push hf_origin master:main