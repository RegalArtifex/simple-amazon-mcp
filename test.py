import asyncio
import json
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
import os

# Define the server parameters to run the local MCP server
# We use the same command as defined in mcp.json
server_params = StdioServerParameters(
    command="python3",
    args=["-m", "simple_amazon_mcp.server"],
    env={**os.environ, "PYTHONPATH": "src"}
)

async def run_test():
    print("Connecting to MCP server...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # List available tools
                response = await session.list_tools()
                tools = response.tools
                print(f"Connected to MCP server. Available tools: {[t.name for t in tools]}")

                # Map MCP tools to Ollama tool format
                ollama_tools = []
                for tool in tools:
                    ollama_tools.append({
                        'type': 'function',
                        'function': {
                            'name': tool.name,
                            'description': tool.description,
                            'parameters': tool.inputSchema,
                        },
                    })

                # Prompts to test
                prompts = [
                    "Search for 'mechanical keyboard' on Amazon and give me the top 3 results.",
                    "Can you get the details for this product: https://www.amazon.in/IBELL-ID13-75-Armature-selector-variable/dp/B0BBLFNQHJ"
                ]

                # Using llama3.1 for testing
                model = 'llama3.1:latest'

                for prompt in prompts:
                    print(f"\n" + "="*50)
                    print(f"USER PROMPT: {prompt}")
                    print("="*50)
                    
                    messages = [{'role': 'user', 'content': prompt}]
                    
                    # First chat call to see if model wants to use tools
                    response = ollama.chat(
                        model=model,
                        messages=messages,
                        tools=ollama_tools,
                    )

                    # Process potential tool calls
                    if response.get('message', {}).get('tool_calls'):
                        messages.append(response['message'])
                        
                        for tool_call in response['message']['tool_calls']:
                            tool_name = tool_call['function']['name']
                            tool_args = tool_call['function']['arguments']
                            
                            print(f"DEBUG: Model calling tool '{tool_name}' with args: {tool_args}")
                            
                            # Execute tool via MCP session
                            try:
                                result = await session.call_tool(tool_name, tool_args)
                                
                                # Process the result (it's a CallToolResult)
                                if result.isError:
                                    content = f"Error: {result.content}"
                                else:
                                    # result.content is a list of TextContent/ImageContent/etc.
                                    content = "\n".join([c.text for c in result.content if hasattr(c, 'text')])
                                
                                print(f"DEBUG: Tool returned {len(content)} characters.")
                                
                                messages.append({
                                    'role': 'tool',
                                    'content': content,
                                })
                            except Exception as e:
                                print(f"ERROR calling tool: {e}")
                                messages.append({
                                    'role': 'tool',
                                    'content': f"Error: {str(e)}",
                                })
                        
                        # Second chat call to get final response
                        print("DEBUG: Generating final response with tool results...")
                        final_response = ollama.chat(
                            model=model,
                            messages=messages,
                        )
                        print(f"\nAI RESPONSE:\n{final_response['message']['content']}")
                    else:
                        print(f"\nAI RESPONSE (no tool call):\n{response['message']['content']}")
                        
    except Exception as e:
        print(f"FAILED to run test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Allow passing a custom prompt as argument
        test_prompt = " ".join(sys.argv[1:])
        # Reset prompts to just this one
        prompts = [test_prompt]
    
    asyncio.run(run_test())
