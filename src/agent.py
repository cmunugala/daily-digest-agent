import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI, pydantic_function_tool
from pydantic import BaseModel, Field
from typing import Optional

from tools import search_arxiv, search_hacker_news, search_the_guardian


load_dotenv()


# pydantic models for responses
class DailyDigestResponse(BaseModel):
    daily_digest: str = Field(
        description="A concise daily digest containing relevant articles and posts related the user's original query. Should be in human readable text and should include urls to the articles/website that are cited."
    )


# pydantic models for tool calls
class SearchArxivTool(BaseModel):
    query: str = Field(description="The search query to find relevant academic papers.")
    max_results: Optional[int] = Field(
        default=1, description="The maximum number of search results to return."
    )


class SearchHackerNewsTool(BaseModel):
    query: str = Field(
        description="The search query to find relevant Hacker News stories."
    )
    max_results: Optional[int] = Field(
        default=1, description="The maximum number of search results to return."
    )


class SearchTheGuardianTool(BaseModel):
    query: str = Field(
        description="The search query to find relevant news articles from The Guardian."
    )
    api_key: str = Field(description="API key for The Guardian Open Platform.")
    max_results: Optional[int] = Field(
        default=1, description="The maximum number of search results to return."
    )


# list tools available to the agent
tools = [
    pydantic_function_tool(SearchArxivTool, name="search_arxiv"),
    pydantic_function_tool(SearchHackerNewsTool, name="search_hacker_news"),
    pydantic_function_tool(SearchTheGuardianTool, name="search_the_guardian"),
]


# call function for tools
def call_function(name, args):
    if name == "search_arxiv":
        return search_arxiv(args["query"], args.get("max_results", 1))
    elif name == "search_hacker_news":
        return search_hacker_news(args["query"], args.get("max_results", 1))
    elif name == "search_the_guardian":
        return search_the_guardian(
            args["query"], args["api_key"], args.get("max_results", 1)
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# main agent loop
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
current_date = datetime.now().strftime("%Y-%m-%d")


while True:
    user_question = input("What would you like to read/learn about?: ")

    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. CRITICAL: Today is {current_date}. You help the user by learning about what they want to read/learn about and then providing a concise daily digest containing relevant articles and posts related the user's original query. The user will ask you a question about what they want to read/learn about, and you will use the tools available to you to find relevant information. You should use the tools to find relevant information and then provide a concise daily digest in human readable text that includes urls to the articles/website that are cited.",
        },
        {"role": "user", "content": user_question},
    ]

    max_iterations = 5
    for _ in range(max_iterations):
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            response_format=DailyDigestResponse,
        )
        response_message = completion.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                print(
                    f"DEBUG: LLM is calling tool with args:{tool_call.function.arguments}"
                )
                name = tool_call.function.name
                args = tool_call.function.parsed_arguments.model_dump()

                print(f"🛠️ Agent calling tool: {name}")
                result = call_function(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

            continue

        else:
            break

    if response_message.tool_calls:
        print("Max iterations reached without a final answer.")

    final_response = response_message.parsed

    print(final_response.daily_digest)
