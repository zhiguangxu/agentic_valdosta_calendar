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
        uv run uvicorn backend.main:app --reload --port 8000

To start the frontend locally:
    from the frontend folder: 
        npm start
