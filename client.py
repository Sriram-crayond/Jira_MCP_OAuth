import asyncio
import os
import requests
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# ---------------- OAUTH TOKEN FETCH ----------------
TOKEN_ENDPOINT = "https://leaseless-long-commutative.ngrok-free.dev/get-token"

def fetch_oauth_creds():
    """Fetch OAuth credentials from the token endpoint"""
    resp = requests.get(
        TOKEN_ENDPOINT,
        params={"provider": "jira"},
        headers={"x-api-key": "scrummaster123"},  # ✅ Fixed: Added API key
        verify=False
    )
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise Exception("No OAuth tokens returned.")

    item = data[0]
    return item["access_token"], item["cloud_id"]


def manual_oauth_creds():
    """Alternative: Manually input credentials"""
    print("\n=== Manual OAuth Credentials ===")
    access_token = input("Enter Jira Access Token: ").strip()
    cloud_id = input("Enter Jira Cloud ID: ").strip()
    return access_token, cloud_id


async def main():
    # Choose credential method
    print("\n[*] Choose credential method:")
    print("1. Fetch from OAuth endpoint (auto)")
    print("2. Enter manually")
    choice = input("Enter choice (1/2): ").strip()

    if choice == "2":
        print("[*] Using manual credentials...")
        access_token, cloud_id = manual_oauth_creds()
    else:
        print("[*] Fetching OAuth credentials from endpoint...")
        access_token, cloud_id = fetch_oauth_creds()
    
    print(f"    Access Token: {access_token[:40]}..." if len(access_token) > 40 else access_token)
    print(f"    Cloud ID: {cloud_id}")

    # ---------------- Build MCP client with OAuth headers ----------------
    print("[*] Creating MultiServerMCPClient with OAuth headers...")
    
    client = MultiServerMCPClient(
        {
            "jira": {
                "url": "https://Jiramcpoauth.fastmcp.app/mcp", #"http://localhost:3000/mcp" -> for local http transport testing
                "transport": "streamable_http",
                "headers": {
                    "x-user-jira-access-token": access_token,  #  OAuth token
                    "x-user-jira-cloud-id": cloud_id           #  Cloud ID
                }
            }
        }
    )
    
    tools = await client.get_tools()
    print(f"[*] Loaded {len(tools)} Jira tools")
    
    # Initialize Gemini LLM agent
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
        system_instruction=(
            "You are an autonomous Jira workflow agent. "
            "Your role is to coordinate multiple Jira operations end-to-end "
            "— retrieving users, searching issues, adding comments, assigning, transitioning, "
            "and creating issues — all through available MCP tools. "
            "Always execute steps in logical order and return a concise summary at the end, "
            "including all relevant IDs, statuses, and outcomes. "
            "Communicate like a structured automation controller."
        )
    )

    agent = create_react_agent(llm, tools)
    
    print("[*] Agent Ready. Type 'quit' to exit.\n")
    
    test_prompt = input("You: ").strip()

    while test_prompt.lower() != "quit":
        try:
            response = await agent.ainvoke({
                "messages": [{"role": "user", "content": test_prompt}]
            })
            
            print("\n" + "="*60)
            
            tool_calls = {}
            for msg in response["messages"]:
                msg_type = msg.__class__.__name__
                if msg_type == "ToolMessage":
                    tool_name = msg.name
                    if tool_name not in tool_calls:
                        tool_calls[tool_name] = 0
                    tool_calls[tool_name] += 1
                    print(f"[TOOL #{tool_calls[tool_name]}] {tool_name}")
                    # Uncomment to see tool results:
                    print(f"[RESULT] {msg.content}\n")
                elif msg_type == "AIMessage":
                    print(f"\n[AI RESPONSE]\n{msg.content}\n")
                elif msg_type == "HumanMessage":
                    print(f"[HUMAN QUERY]\n{msg.content[:100]}...\n")
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n[ERROR] {str(e)}\n")
        
        test_prompt = input("You: ").strip()
    
    print("[*] Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())