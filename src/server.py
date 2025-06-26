import os
from fastapi import FastAPI, HTTPException
from github import Github
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN not found in environment variables. Please set it in your .env file.")

github_client = Github(GITHUB_TOKEN)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the MCP GitHub Server!"}

@app.get("/github/me")
def github_me():
    try:
        user = github_client.get_user()
        return {"login": user.login, "name": user.name, "public_repos": user.public_repos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub authentication failed: {str(e)}")

# Additional endpoints for GitHub integration can be added here

# Placeholder for GitHub integration endpoints 