import json
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, pydantic_function_tool
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.database import engine, init_db
from src.models import Article, Interest, User
from src.tools import search_arxiv, search_hacker_news, search_the_guardian

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


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
        default=5, description="The maximum number of search results to return."
    )


class SearchHackerNewsTool(BaseModel):
    query: str = Field(
        description="The search query to find relevant Hacker News stories."
    )
    max_results: Optional[int] = Field(
        default=5, le=10, description="The maximum number of search results to return."
    )


class SearchTheGuardianTool(BaseModel):
    query: str = Field(
        description="The search query to find relevant news articles from The Guardian."
    )
    max_results: Optional[int] = Field(
        default=5, description="The maximum number of search results to return."
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
        interest_list = [i.topic for i in past_interests]
        context_string = ", ".join(interest_list)

        if current_query not in interest_list:
            # Store the current request as a new Interest
            new_interest = Interest(topic=current_query, user_id=user.id)
            session.add(new_interest)
            session.commit()

        return context_string


def get_new_articles(username: str, found_articles: list[dict]):
    """
    found_articles: A list of dicts with 'title', 'url', and 'source'.
    """
    new_to_user = []

    with Session(engine) as session:
        # 1. Fetch the user within this session
        user = session.exec(select(User).where(User.name == username)).first()
        if not user:
            return []  # Safety check

        # 2. Get a set of URLs this user has already seen
        seen_urls = {article.url for article in user.seen_articles}

        for item in found_articles:
            url = item.get("url")

            if url in seen_urls:
                continue

            # 3. Check if article exists globally
            db_article = session.exec(select(Article).where(Article.url == url)).first()

            if not db_article:
                db_article = Article(
                    title=item.get("title", "No Title"),
                    url=url,
                    source=item.get("source", "Unknown"),
                )
                session.add(db_article)
                # We need to flush or commit to get an ID for db_article if it's new
                session.flush()

            new_to_user.append(db_article)

        session.commit()

        # Convert to dicts so the LLM can read them easily
        return [
            {"title": a.title, "url": a.url, "source": a.source} for a in new_to_user
        ]


def mark_articles_as_seen(username: str, digest_text: str):
    # Extract all URLs from the LLM's response
    urls = re.findall(r"https?://[^\s)\]]+", digest_text)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.name == username)).first()
        for url in urls:
            article = session.exec(select(Article).where(Article.url == url)).first()
            if article and article not in user.seen_articles:
                user.seen_articles.append(article)
        session.commit()


# main llm workflow loop
def run_daily_digest_workflow(username: str, user_question: str):
    init_db()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    current_date = datetime.now().strftime("%Y-%m-%d")

    # list tools available to the agent
    tools = [
        pydantic_function_tool(SearchArxivTool, name="search_arxiv"),
        pydantic_function_tool(SearchHackerNewsTool, name="search_hacker_news"),
        pydantic_function_tool(SearchTheGuardianTool, name="search_the_guardian"),
    ]

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
            "content": f"""You are a helpful assistant. You help the user by learning about what they want to read/learn about and then providing a concise daily digest containing relevant articles and posts related the user's original query. The user will ask you a question about what they want to read/learn about, and you will use the tools available to you to find relevant information. You should use the tools to find relevant information and then provide a concise daily digest in human readable text that includes urls to the articles/website that are cited. 
            
            CRITICAL: Today is {current_date}. We want to prioritize more recent articles/blogs/information. 
            
            The user's past interests are: {personalized_context}. You should still focus on the primary user query, but you can use the user's past interests to provide a more personalized experience if there are synergies between the user's past interests and the user's current query.
            
            If a tool returns a message stating that no new articles were found, do not invent news. Simply inform the user that there are no articles available that they haven't seen.""",
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
            max_attempts = 3
            current_max = args.get("max_results", 5)
            filtered_result = []

            # loop to get results if by chance user has seen all the articles already
            for attempt in range(max_attempts):
                args["max_results"] = current_max
                result = call_function(name, args)
                filtered_result = get_new_articles(username, result)

                if len(filtered_result) > 0:
                    break
                current_max += 5

            if not filtered_result:
                tool_output = "I searched extensively but found no new articles related to this query."
            else:
                tool_output = json.dumps(filtered_result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                }
            )

    daily_digest_completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini", messages=messages, response_format=DailyDigestResponse
    )

    daily_digest_response_message = daily_digest_completion.choices[0].message
    digest_output = daily_digest_response_message.parsed.daily_digest
    mark_articles_as_seen(username, digest_output)
    return digest_output


if __name__ == "__main__":
    username = input("Enter your username: ")
    user_question = input("What would you like to read/learn about today?:")
    digest = run_daily_digest_workflow(username, user_question)
    print(digest)
