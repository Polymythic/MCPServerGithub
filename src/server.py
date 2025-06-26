import os
from fastapi import FastAPI, HTTPException, Body
from github import Github
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List

# Load environment variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN not found in environment variables. Please set it in your .env file.")

github_client = Github(GITHUB_TOKEN)

app = FastAPI()

class BranchActionRequest(BaseModel):
    repo_name: str
    branch_name: str
    base_branch: Optional[str] = None  # For creating a branch

class PullRequestRequest(BaseModel):
    repo_name: str
    title: str
    body: Optional[str] = ""
    head: str  # The name of the branch where your changes are implemented
    base: str  # The name of the branch you want the changes pulled into

class RepoCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    private: bool = False
    org_name: Optional[str] = None

class IssueCreateRequest(BaseModel):
    repo_name: str
    title: str
    body: Optional[str] = ""
    assignees: Optional[List[str]] = []
    labels: Optional[List[str]] = []

class IssueCommentRequest(BaseModel):
    repo_name: str
    issue_number: int
    comment: str

class IssueStateRequest(BaseModel):
    repo_name: str
    issue_number: int
    state: str  # 'open' or 'closed'

class PRMergeRequest(BaseModel):
    repo_name: str
    pr_number: int
    commit_message: Optional[str] = None

class PRCloseRequest(BaseModel):
    repo_name: str
    pr_number: int

class BranchDeleteRequest(BaseModel):
    repo_name: str
    branch_name: str

class BranchCompareRequest(BaseModel):
    repo_name: str
    base: str
    head: str

class WebhookListRequest(BaseModel):
    repo_name: str

class CollaboratorRequest(BaseModel):
    repo_name: str
    username: str
    permission: Optional[str] = "push"

class PRCommentRequest(BaseModel):
    repo_name: str
    pr_number: int
    comment: str

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

@app.get("/github/branches")
def list_branches(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        branches = repo.get_branches()
        return {"branches": [b.name for b in branches]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list branches: {str(e)}")

@app.post("/github/branch/create")
def create_branch(req: BranchActionRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        base = req.base_branch or repo.get_branch("main").name
        source = repo.get_branch(base)
        repo.create_git_ref(ref=f"refs/heads/{req.branch_name}", sha=source.commit.sha)
        return {"message": f"Branch '{req.branch_name}' created from '{base}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")

@app.get("/github/pull-requests")
def list_pull_requests(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        pulls = repo.get_pulls(state="open")
        return {"pull_requests": [{"id": pr.id, "title": pr.title, "head": pr.head.ref, "base": pr.base.ref} for pr in pulls]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pull requests: {str(e)}")

@app.post("/github/pull-request/create")
def create_pull_request(req: PullRequestRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        pr = repo.create_pull(title=req.title, body=req.body or "", head=req.head, base=req.base)
        return {"message": "Pull request created", "url": pr.html_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pull request: {str(e)}")

@app.get("/github/repos")
def list_repos():
    try:
        repos = github_client.get_user().get_repos()
        return {"repositories": [r.full_name for r in repos]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")

@app.get("/github/repo")
def get_repo(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        return {"name": repo.name, "full_name": repo.full_name, "description": repo.description, "private": repo.private, "topics": repo.get_topics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository: {str(e)}")

@app.post("/github/repo/create")
def create_repo(req: RepoCreateRequest):
    try:
        if req.org_name:
            org = github_client.get_organization(req.org_name)
            repo = org.create_repo(name=req.name, description=req.description or "", private=bool(req.private))
        else:
            user = github_client.get_user()
            repo = user.create_repo(name=req.name, description=req.description or "", private=bool(req.private))
        return {"message": "Repository created", "url": repo.html_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")

@app.get("/github/issues")
def list_issues(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        issues = repo.get_issues()
        return {"issues": [{"number": i.number, "title": i.title, "state": i.state} for i in issues]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list issues: {str(e)}")

@app.post("/github/issue/create")
def create_issue(req: IssueCreateRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        issue = repo.create_issue(title=req.title, body=req.body or "", assignees=req.assignees or [], labels=req.labels or [])
        return {"message": "Issue created", "number": issue.number, "url": issue.html_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")

@app.post("/github/issue/comment")
def comment_issue(req: IssueCommentRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        issue = repo.get_issue(number=req.issue_number)
        comment = issue.create_comment(req.comment)
        return {"message": "Comment added", "url": comment.html_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to comment on issue: {str(e)}")

@app.post("/github/issue/state")
def set_issue_state(req: IssueStateRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        issue = repo.get_issue(number=req.issue_number)
        issue.edit(state=req.state)
        return {"message": f"Issue state set to {req.state}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set issue state: {str(e)}")

@app.post("/github/pr/merge")
def merge_pr(req: PRMergeRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        pr = repo.get_pull(req.pr_number)
        pr.merge(commit_message=req.commit_message or "Merged by MCP server")
        return {"message": "Pull request merged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge pull request: {str(e)}")

@app.post("/github/pr/close")
def close_pr(req: PRCloseRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        pr = repo.get_pull(req.pr_number)
        pr.edit(state="closed")
        return {"message": "Pull request closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close pull request: {str(e)}")

@app.post("/github/pr/comment")
def comment_pr(req: PRCommentRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        pr = repo.get_pull(req.pr_number)
        comment = pr.create_issue_comment(req.comment)
        return {"message": "Comment added", "url": comment.html_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to comment on pull request: {str(e)}")

@app.get("/github/pr/reviews")
def list_pr_reviews(repo_name: str, pr_number: int):
    try:
        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        reviews = pr.get_reviews()
        return {"reviews": [{"user": r.user.login, "state": r.state, "body": r.body} for r in reviews]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pull request reviews: {str(e)}")

@app.post("/github/branch/delete")
def delete_branch(req: BranchDeleteRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        ref = repo.get_git_ref(f"heads/{req.branch_name}")
        ref.delete()
        return {"message": f"Branch '{req.branch_name}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete branch: {str(e)}")

@app.post("/github/branch/compare")
def compare_branches(req: BranchCompareRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        comparison = repo.compare(req.base, req.head)
        return {"ahead_by": comparison.ahead_by, "behind_by": comparison.behind_by, "commits": [c.sha for c in comparison.commits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare branches: {str(e)}")

@app.get("/github/webhooks")
def list_webhooks(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        hooks = repo.get_hooks()
        return {"webhooks": [{"id": h.id, "url": h.config.get('url')} for h in hooks]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list webhooks: {str(e)}")

@app.get("/github/collaborators")
def list_collaborators(repo_name: str):
    try:
        repo = github_client.get_repo(repo_name)
        users = repo.get_collaborators()
        return {"collaborators": [u.login for u in users]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collaborators: {str(e)}")

@app.post("/github/collaborator/add")
def add_collaborator(req: CollaboratorRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        repo.add_to_collaborators(req.username, permission=req.permission or "push")
        return {"message": f"Collaborator '{req.username}' added with permission '{req.permission or 'push'}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add collaborator: {str(e)}")

@app.post("/github/collaborator/remove")
def remove_collaborator(req: CollaboratorRequest):
    try:
        repo = github_client.get_repo(req.repo_name)
        repo.remove_from_collaborators(req.username)
        return {"message": f"Collaborator '{req.username}' removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove collaborator: {str(e)}")

@app.get("/github/teams")
def list_teams(org_name: str):
    try:
        org = github_client.get_organization(org_name)
        teams = org.get_teams()
        return {"teams": [t.name for t in teams]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {str(e)}")

@app.get("/github/rate-limit")
def rate_limit():
    try:
        rate = github_client.get_rate_limit()
        return {"core": {"limit": rate.core.limit, "remaining": rate.core.remaining, "reset": str(rate.core.reset)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": "0.1.0"}

# Additional endpoints for GitHub integration can be added here

# Placeholder for GitHub integration endpoints 