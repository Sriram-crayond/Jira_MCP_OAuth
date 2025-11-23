# Jira MCP Server with OAuth Authentication

A FastMCP server that provides 11 Jira tools through the Model Context Protocol (MCP), with OAuth-based authentication supporting multiple users. Includes a LangGraph agent powered by Google Gemini for autonomous Jira workflow automation.

## Architecture

```
┌─────────────┐      OAuth Headers      ┌──────────────────┐
│   Client    │ ──────────────────────> │  FastMCP Server  │
│  (Agent)    │   (access_token + ID)   │  (Deployed/Local)│
└─────────────┘                         └──────────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Jira Cloud  │
                                        │     API      │
                                        └──────────────┘
```

## 📁 Project Structure

```
MCP_JIRA_OAuth/
├── server.py          # FastMCP server with 11 Jira tools
├── client.py          # LangGraph agent with Gemini LLM
├── requirements.txt   # Python dependencies
├── .env              # Environment variables (create this)
├── .gitignore        # Git ignore file
└── README.md         # This file
```

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Sriram-crayond/Jira_MCP_OAuth
cd MCP_JIRA_OAuth
pip install -r requirements.txt
```

### 2. Create `.env` File

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key: https://aistudio.google.com/apikey

### 3. Run Local Server or deploy it in fastmcp cloud (Already did)

```bash
python server.py
```

Server runs on: `http://localhost:3000/mcp`

choose the Local Server or Deployed Server: 
- **Option 1**: Use local server (`localhost:3000`)
- **Option 2**: Use deployed server (FastMCP Cloud) -> can be changed in the client.py url (line - 63)

### 4. Run Client

```bash
python client.py
```

Choose:
- **Option 1**: Auto-fetch OAuth credentials from endpoint (make sure to refresh the ngrok connection)
- **Option 2**: Manually enter `access_token` and `cloud_id`


##  Available Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `jira_search_issues` | Search issues using JQL |
| 2 | `jira_get_issue` | Get detailed issue information |
| 3 | `jira_create_issue` | Create a new issue |
| 4 | `jira_update_issue` | Update issue fields |
| 5 | `jira_add_comment` | Add comment to issue |
| 6 | `jira_get_transitions` | Get available status transitions |
| 7 | `jira_transition_issue` | Change issue status |
| 8 | `jira_assign_issue` | Assign issue to user |
| 9 | `jira_get_project` | Get project details |
| 10 | `jira_get_all_users` | List workspace users |
| 11 | `jira_get_issue_watchers` | Get issue watchers |

##  OAuth Setup

The server reads OAuth credentials from HTTP headers:
- `x-user-jira-access-token`: Jira OAuth access token
- `x-user-jira-cloud-id`: Jira Cloud ID

### Required OAuth Scopes
```
manage:jira-project
read:jira-work
write:jira-work
read:jira-user
offline_access
```

## Usage Examples

```
You: Create a new task in project <project-key> (KAN) with summary "Setup OAuth"

You: Get all users in the workspace

You: Assign issue <issue_name> (KAN-3) to <user_name>

You: Update KAN-3 priority to High and summary to "Urgent fix"

You: Search for all high priority issues in project KAN

You: Transition KAN-3 to Done
```

## Dependencies

- **fastmcp**: MCP server framework
- **atlassian-python-api**: Jira Python SDK
- **python-dotenv**: Environment variable management
- **langchain-mcp-adapters**: MCP client for LangChain
- **langgraph**: Agent framework
- **langchain-google-genai**: Google Gemini integration


## Links

- FastMCP Cloud: https://fastmcp.cloud
- Atlassian OAuth: https://developer.atlassian.com/console/myapps
- Gemini API: https://aistudio.google.com/apikey