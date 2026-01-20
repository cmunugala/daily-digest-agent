import json
import os
from datetime import datetime
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, pydantic_function_tool
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from database import engine
from models import Interest, User
from tools import search_arxiv, search_hacker_news, search_the_guardian

load_dotenv()


# pydantic models for responses
class DailyDigestResponse(BaseModel):
    daily_digest: str = Field(
        description="A concise daily digest describing what is going on in world related to the users query. If applicable, the response should cite articles and posts that were found using tools."
    )


class Category(str, Enum):
    ACADEMIC = "Academic"
    SOFTWARE = "Software"
    GENERAL_NEWS = "General News"


class QueryClassificationResponse(BaseModel):
    classification: Category = Field(
        description="The category that best describes the user's query. This should be one of: Academic, Software, or General News."
    )
    reasoning: str = Field(
        description="A brief explanation of why the query was classified into this category."
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
    max_results: Optional[int] = Field(
        default=1, description="The maximum number of search results to return."
    )


# call function for tools
def call_function(name, args):
    if name == "search_arxiv":
        return search_arxiv(args["query"], args.get("max_results", 1))
    elif name == "search_hacker_news":
        return search_hacker_news(args["query"], args.get("max_results", 1))
    elif name == "search_the_guardian":
        return search_the_guardian(
            args["query"], os.getenv("GUARDIAN_API_KEY"), args.get("max_results", 1)
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# Get personalized context based on user's past interests and store new interests
def get_personalized_context(username: str, current_query: str):
    with Session(engine) as session:
        # 1. Get or Create User
        user = session.exec(select(User).where(User.name == username)).first()
        if not user:
            user = User(name=username)
            session.add(user)
            session.commit()
            session.refresh(user)

        # Pull ALL past interests for the LLM context
        past_interests = session.exec(
            select(Interest).where(Interest.user_id == user.id)
        ).all()

        # Format the interests for the prompt
        interest_list = [i.topic for i in past_interests][0:10]
        context_string = ", ".join(interest_list)

        # Store the current request as a new Interest
        new_interest = Interest(topic=current_query, user_id=user.id)
        session.add(new_interest)
        session.commit()

        return context_string


# main llm workflow loop
if __name__ == "__main__":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    current_date = datetime.now().strftime("%Y-%m-%d")

    # list tools available to the agent
    tools = [
        pydantic_function_tool(SearchArxivTool, name="search_arxiv"),
        pydantic_function_tool(SearchHackerNewsTool, name="search_hacker_news"),
        pydantic_function_tool(SearchTheGuardianTool, name="search_the_guardian"),
    ]
    username = input("Enter your username: ")
    user_question = input("What would you like to read/learn about today?:")

    personalized_context = get_personalized_context(username, user_question)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. You help decide whether the user's query is related to something academic/work related, software, or general news.",
        },
        {"role": "user", "content": user_question},
    ]

    query_classification_completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        response_format=QueryClassificationResponse,
    )

    category = query_classification_completion.choices[0].message.parsed.classification

    if category == "Academic":
        tool_name = "search_arxiv"
    elif category == "Software":
        tool_name = "search_hacker_news"
    else:
        tool_name = "search_the_guardian"

    messages = [
        {
            "role": "system",
            "content": """You are a helpful assistant. You help the user by learning about what they want to read/learn about and then providing a concise daily digest containing relevant articles and posts related the user's original query. The user will ask you a question about what they want to read/learn about, and you will use the tools available to you to find relevant information. You should use the tools to find relevant information and then provide a concise daily digest in human readable text that includes urls to the articles/website that are cited. 
            
            CRITICAL: Today is {current_date}. We want to prioritize more recent articles/blogs/information. 
            
            The user's past interests are: {personalized_context}. You should still focus on the primary user query, but you can use the user's past interests to provide a more personalized experience if there are synergies between the user's past interests and the user's current query.""",
        },
        {"role": "user", "content": user_question},
    ]

    tool_call_completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice={
            "type": "function",
            "function": {"name": tool_name},
        },
    )

    tool_call_response_message = tool_call_completion.choices[0].message
    messages.append(tool_call_response_message)

    if tool_call_response_message.tool_calls:
        for tool_call in tool_call_response_message.tool_calls:
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

    daily_digest_completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini", messages=messages, response_format=DailyDigestResponse
    )

    daily_digest_response_message = daily_digest_completion.choices[0].message
    print(daily_digest_response_message.parsed.daily_digest)
