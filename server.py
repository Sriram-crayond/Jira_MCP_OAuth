from fastmcp import FastMCP, Context as MCPContext
from fastmcp.server.dependencies import get_http_headers
from atlassian import Jira
from typing import Optional, Dict, List, Any

# Initialize FastMCP server
mcp = FastMCP("jira-mcp-server")


def get_jira_client() -> Jira:
    """
    Extract OAuth credentials from request headers and create Jira client.
    
    Expected headers:
    - x-user-jira-access-token: OAuth access token
    - x-user-jira-cloud-id: Jira cloud ID
    """
    headers = get_http_headers()
    
    access_token = headers.get("x-user-jira-access-token")
    cloud_id = headers.get("x-user-jira-cloud-id")
    
    if not access_token or not cloud_id:
        raise ValueError(
            f"Missing required OAuth headers. "
            f"Found headers: {list(headers.keys())}"
        )
    
    # Construct Jira URL from cloud_id
    jira_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"
    
    # Create Jira client with OAuth token
    jira_client = Jira(
        url=jira_url,
        token=access_token,  # OAuth token instead of username/password
        cloud=True
    )
    
    return jira_client


def get_user_account_id(jira_client: Jira, email_or_username: str) -> Optional[str]:
    """
    Helper function to get Jira user account ID from email or username.
    Required for Jira Cloud assignee field.
    """
    try:
        users = jira_client.user_find_by_user_string(query=email_or_username)
        if users and len(users) > 0:
            return users[0].get('accountId')
        return None
    except Exception as e:
        print(f"Error finding user: {e}")
        return None


@mcp.tool()
def jira_search_issues(jql: str, max_results: int = 50, fields: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for Jira issues using JQL (Jira Query Language).
    
    Args:
        jql: JQL query string (e.g., 'project = PROJ AND status = "In Progress"')
        max_results: Maximum number of results to return (default: 50, max: 100)
        fields: Comma-separated list of fields to return (optional)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - total: Total number of matching issues
        - returned: Number of issues returned in this response
        - jql: The JQL query used
        - issues: List of issue objects with key, summary, status, assignee, etc.
    """
    try:
        jira_client = get_jira_client()
        
        if not fields:
            fields = "key,summary,status,assignee,priority,issuetype,created,updated"
        
        results = jira_client.jql(
            jql=jql,
            limit=min(max_results, 100),
            fields=fields
        )
        
        issues = []
        for issue in results.get('issues', []):
            fields_data = issue.get('fields', {})
            issues.append({
                "key": issue.get('key'),
                "summary": fields_data.get('summary'),
                "status": fields_data.get('status', {}).get('name'),
                "assignee": fields_data.get('assignee', {}).get('displayName') if fields_data.get('assignee') else 'Unassigned',
                "priority": fields_data.get('priority', {}).get('name') if fields_data.get('priority') else None,
                "issue_type": fields_data.get('issuetype', {}).get('name'),
                "created": fields_data.get('created'),
                "updated": fields_data.get('updated'),
                "url": f"https://jira.atlassian.com/browse/{issue.get('key')}"
            })
        
        return {
            "success": True,
            "total": results.get('total', 0),
            "returned": len(issues),
            "jql": jql,
            "issues": issues
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to execute JQL search: {jql}"
        }


@mcp.tool()
def jira_get_issue(issue_key: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific Jira issue.
    
    Args:
        issue_key: The issue key (e.g., 'SCRUM-123', 'PROJ-456')
    
    Returns:
        Dictionary containing comprehensive issue details
    """
    try:
        jira_client = get_jira_client()
        issue = jira_client.issue(issue_key)
        fields = issue.get('fields', {})
        
        return {
            "success": True,
            "issue_key": issue.get('key'),
            "summary": fields.get('summary'),
            "description": fields.get('description'),
            "status": fields.get('status', {}).get('name'),
            "issue_type": fields.get('issuetype', {}).get('name'),
            "priority": fields.get('priority', {}).get('name') if fields.get('priority') else None,
            "assignee": fields.get('assignee', {}).get('displayName') if fields.get('assignee') else 'Unassigned',
            "reporter": fields.get('reporter', {}).get('displayName'),
            "created": fields.get('created'),
            "updated": fields.get('updated'),
            "labels": fields.get('labels', []),
            "components": [c.get('name') for c in fields.get('components', [])],
            "project": fields.get('project', {}).get('name'),
            "url": f"https://jira.atlassian.com/browse/{issue.get('key')}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to retrieve issue {issue_key}"
        }


@mcp.tool()
def jira_add_comment(issue_key: str, comment: str) -> Dict[str, Any]:
    """
    Add a comment to a Jira issue.
    
    Args:
        issue_key: The issue key (e.g., 'SCRUM-123')
        comment: The comment text to add
    
    Returns:
        Dictionary containing success status and comment ID
    """
    try:
        jira_client = get_jira_client()
        result = jira_client.issue_add_comment(issue_key, comment)
        
        return {
            "success": True,
            "issue_key": issue_key,
            "comment_id": result.get('id') if result else None,
            "message": f"Successfully added comment to {issue_key}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add comment to {issue_key}"
        }


@mcp.tool()
def jira_transition_issue(issue_key: str, status: str) -> Dict[str, Any]:
    """
    Transition a Jira issue to a new workflow status.
    
    Args:
        issue_key: The unique key of the Jira issue (e.g., "PROJ-1234")
        status: The target status name (e.g., "Done", "In Progress", "To Do")
    
    Returns:
        Dictionary with success status, issue_key, new_status, and message
    """
    try:
        jira_client = get_jira_client()
        status = str(status).strip()

        # Get transition ID directly using helper
        transition_id = jira_client.get_transition_id_to_status_name(issue_key, status)

        if not transition_id:
            return {
                "success": False,
                "error": f"No transition found to status '{status}'",
                "message": f"Available transitions might not include '{status}'"
            }

        # Use Jira client's internal handler
        jira_client.set_issue_status_by_transition_id(issue_key, transition_id)

        return {
            "success": True,
            "issue_key": issue_key,
            "new_status": status,
            "message": f"Successfully transitioned {issue_key} to '{status}'"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to transition issue {issue_key}"
        }


@mcp.tool()
def jira_get_transitions(issue_key: str) -> Dict[str, Any]:
    """
    Get all available status transitions for a Jira issue.
    
    Args:
        issue_key: The issue key (e.g., 'SCRUM-123')
    
    Returns:
        Dictionary with current_status and available transitions
    """
    try:
        jira_client = get_jira_client()
        
        # Get current issue status
        issue = jira_client.issue(issue_key)
        current_status = issue.get('fields', {}).get('status', {}).get('name')
        
        # Get available transitions
        transitions_response = jira_client.get_issue_transitions(issue_key)
        
        if isinstance(transitions_response, list):
            transitions_list = transitions_response
        else:
            transitions_list = []
        
        transitions = []
        for trans in transitions_list:
            transitions.append({
                "id": trans.get('id'),
                "name": trans.get('name'),
                "to_status": trans['to']['name'] if isinstance(trans.get('to'), dict) else trans.get('to')
            })
        
        return {
            "success": True,
            "issue_key": issue_key,
            "current_status": current_status,
            "transitions": transitions
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get transitions for {issue_key}"
        }


@mcp.tool()
def jira_create_issue(project_key: str, summary: str, issue_type: str, 
                     description: Optional[str] = None, priority: Optional[str] = None,
                     assignee: Optional[str] = None, labels: Optional[List[str]] = None,
                     components: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create a new Jira issue.
    
    Args:
        project_key: Project key (e.g., 'SCRUM', 'PROJ')
        summary: Issue title/summary
        issue_type: Type of issue ('Bug', 'Story', 'Task', 'Epic', etc.)
        description: Detailed description (optional)
        priority: Priority level ('High', 'Medium', 'Low', etc.) (optional)
        assignee: Email or username of assignee (optional)
        labels: List of labels to add (optional)
        components: List of component names (optional)
    
    Returns:
        Dictionary with success status, issue_key, and URL
    """
    try:
        jira_client = get_jira_client()
        
        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }
        
        if description:
            fields["description"] = description
        if priority:
            fields["priority"] = {"name": priority}
        if assignee:
            account_id = get_user_account_id(jira_client, assignee)
            if account_id:
                fields["assignee"] = {"accountId": account_id}
        if labels:
            fields["labels"] = labels
        if components:
            fields["components"] = [{"name": comp} for comp in components]
        
        new_issue = jira_client.issue_create(fields=fields)
        issue_key = new_issue.get('key')
        
        return {
            "success": True,
            "issue_key": issue_key,
            "url": f"https://jira.atlassian.com/browse/{issue_key}",
            "message": f"Successfully created issue {issue_key}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create issue in project {project_key}"
        }


@mcp.tool()
def jira_get_project(project_key: str) -> Dict[str, Any]:
    """
    Get detailed information about a Jira project.
    
    Args:
        project_key: The project key (e.g., 'SCRUM', 'PROJ')
    
    Returns:
        Dictionary with project details, issue_types, and components
    """
    try:
        jira_client = get_jira_client()
        project = jira_client.project(project_key)
        
        issue_types = [
            {
                "id": it.get('id'),
                "name": it.get('name'),
                "description": it.get('description')
            }
            for it in project.get('issueTypes', [])
        ]
        
        components = [
            {
                "id": comp.get('id'),
                "name": comp.get('name'),
                "description": comp.get('description')
            }
            for comp in project.get('components', [])
        ]
        
        return {
            "success": True,
            "key": project.get('key'),
            "name": project.get('name'),
            "description": project.get('description'),
            "lead": project.get('lead', {}).get('displayName') if project.get('lead') else None,
            "project_type": project.get('projectTypeKey'),
            "url": f"https://jira.atlassian.com/browse/{project.get('key')}",
            "issue_types": issue_types,
            "components": components
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to retrieve project {project_key}"
        }

@mcp.tool()
def jira_update_issue(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[List[str]] = None,
    components: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update an existing Jira issue's details.
    
    Args:
        issue_key: The issue key (e.g., 'KAN-3', 'SCRUM-123')
        summary: New issue title/summary (optional)
        description: New detailed description (optional)
        priority: New priority level ('Highest', 'High', 'Medium', 'Low', 'Lowest') (optional)
        assignee: Email, username, or account ID of new assignee, or 'unassigned' to remove (optional)
        labels: New list of labels (replaces existing labels) (optional)
        components: New list of component names (replaces existing components) (optional)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - issue_key: The issue that was updated
        - updated_fields: List of fields that were changed
        - message: Success/failure message
    
    Examples:
        - Update summary: jira_update_issue("KAN-3", summary="New title here")
        - Update priority: jira_update_issue("KAN-3", priority="High")
        - Update multiple: jira_update_issue("KAN-3", summary="New title", priority="High", assignee="krithika")
    """
    try:
        jira_client = get_jira_client()
        
        fields = {}
        updated_fields = []
        
        # Update summary
        if summary is not None:
            fields["summary"] = summary
            updated_fields.append("summary")
        
        # Update description
        if description is not None:
            fields["description"] = description
            updated_fields.append("description")
        
        # Update priority
        if priority is not None:
            fields["priority"] = {"name": priority}
            updated_fields.append("priority")
        
        # Update assignee
        if assignee is not None:
            if assignee.lower() in ['unassigned', 'null', 'none', '']:
                fields["assignee"] = None
                updated_fields.append("assignee (unassigned)")
            else:
                # Check if it's an account ID or need to search
                if assignee.startswith('712020:') or (len(assignee) > 20 and '-' in assignee):
                    account_id = assignee
                else:
                    account_id = get_user_account_id(jira_client, assignee)
                
                if account_id:
                    fields["assignee"] = {"accountId": account_id}
                    updated_fields.append(f"assignee ({assignee})")
                else:
                    return {
                        "success": False,
                        "error": f"User '{assignee}' not found",
                        "message": "Please provide a valid email, username, or account ID"
                    }
        
        # Update labels
        if labels is not None:
            fields["labels"] = labels
            updated_fields.append("labels")
        
        # Update components
        if components is not None:
            fields["components"] = [{"name": comp} for comp in components]
            updated_fields.append("components")
        
        # Check if any fields to update
        if not fields:
            return {
                "success": False,
                "error": "No fields provided to update",
                "message": "Provide at least one field to update (summary, description, priority, assignee, labels, or components)"
            }
        
        # Perform the update
        jira_client.update_issue_field(issue_key, fields)
        
        return {
            "success": True,
            "issue_key": issue_key,
            "updated_fields": updated_fields,
            "message": f"Successfully updated {issue_key}: {', '.join(updated_fields)}",
            "url": f"https://jira.atlassian.com/browse/{issue_key}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update issue {issue_key}"
        }

@mcp.tool()
def jira_assign_issue(issue_key: str, assignee: str) -> Dict[str, Any]:
    """
    Assign a Jira issue to a team member.
    
    Args:
        issue_key: The issue key (e.g., 'SCRUM-123')
        assignee: Email or username of the assignee, or 'unassigned' to remove assignee
    
    Returns:
        Dictionary with success status and assignee information
    """
    try:
        jira_client = get_jira_client()
        
        if assignee.lower() in ['unassigned', 'null', 'none']:
            # Unassign the issue
            jira_client.update_issue_field(issue_key, {"assignee": None})
            return {
                "success": True,
                "issue_key": issue_key,
                "assignee": "Unassigned",
                "message": f"Successfully unassigned {issue_key}"
            }
        else:
            # Assign to user
            account_id = get_user_account_id(jira_client, assignee)
            if account_id:
                jira_client.update_issue_field(
                    issue_key,
                    {"assignee": {"accountId": account_id}}
                )
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "assignee": assignee,
                    "message": f"Successfully assigned {issue_key} to {assignee}"
                }
            else:
                return {
                    "success": False,
                    "error": f"User '{assignee}' not found",
                    "message": "Please provide a valid email or username"
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to assign issue {issue_key}"
        }


@mcp.tool()
def jira_get_all_users(max_results: int = 50) -> Dict[str, Any]:
    """
    Get a list of all users in the Jira workspace.
    
    Args:
        max_results: Maximum number of users to return (default: 50, max: 1000)
    
    Returns:
        Dictionary with total count and list of users
    """
    try:
        jira_client = get_jira_client()
        
        # Search for all users (query="." returns all)
        users_response = jira_client.user_find_by_user_string(
            query=".",
            start=0,
            limit=min(max_results, 1000),
            include_inactive_users=True
        )

        users = []
        for user in users_response:
            if user.get('accountType') == 'atlassian':  # Exclude bots
                users.append({
                    "account_id": user.get('accountId'),
                    "display_name": user.get('displayName'),
                    "email": user.get('emailAddress'),
                    "active": user.get('active', True)
                })
        
        return {
            "success": True,
            "total": len(users),
            "users": users
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve users from workspace"
        }


@mcp.tool()
def jira_get_issue_watchers(issue_key: str) -> Dict[str, Any]:
    """
    Get a list of users watching a specific Jira issue.
    
    Args:
        issue_key: The issue key (e.g., 'SCRUM-123')
    
    Returns:
        Dictionary with watcher_count and list of watchers
    """
    try:
        jira_client = get_jira_client()
        watchers_response = jira_client.issue_get_watchers(issue_key)
        
        watchers = []
        for watcher in watchers_response.get('watchers', []):
            watchers.append({
                "account_id": watcher.get('accountId'),
                "display_name": watcher.get('displayName'),
                "email": watcher.get('emailAddress'),
                "active": watcher.get('active', True)
            })
        
        return {
            "success": True,
            "issue_key": issue_key,
            "watcher_count": len(watchers),
            "watchers": watchers
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get watchers for issue {issue_key}"
        }


if __name__ == "__main__":
    # Run with HTTP transport on specified host and port
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3000)