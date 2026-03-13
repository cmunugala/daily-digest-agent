import requests
from sqlmodel import Session, select

import streamlit as st
from src.database import engine, init_db
from src.models import Article, Interest, User

# Page config
st.set_page_config(page_title="Daily Digest Agent", page_icon="📰", layout="wide")

# Initialize database
init_db()


# --- Functions ---
def call_digest_api(username: str, user_question: str) -> str:
    """Calls the backend API to generate a digest."""
    api_url = "http://api:8000/digest"
    response = requests.post(
        api_url, json={"username": username, "user_question": user_question}
    )
    response.raise_for_status()
    return response.json()["digest"]


# --- UI ---
def main():
    st.title("📰 Daily Digest Agent")
    st.markdown(
        """
    Your personalized AI news assistant. Tell me what you're interested in today, 
    and I'll find the latest articles from Arxiv, Hacker News, and The Guardian.
    """
    )

    # Sidebar for User Profile
    with st.sidebar:
        st.header("User Profile")
        username = st.text_input("Enter your username")

        if username:
            with Session(engine) as session:
                user = session.exec(select(User).where(User.name == username)).first()
                if user:
                    st.success(f"Welcome back, {username}!")

                    # Show past interests
                    st.subheader("Your Past Interests")
                    interests = [i.topic for i in user.interests]
                    if interests:
                        for interest in interests[-5:]:  # Last 5
                            st.write(f"- {interest}")
                    else:
                        st.info("No past interests yet.")

                    # Show reading history count
                    st.subheader("Reading Stats")
                    st.write(f"Articles read: {len(user.seen_articles)}")
                else:
                    st.info(f"New user: {username}. A profile will be created.")

    # Main area
    user_question = st.text_input(
        "What would you like to read/learn about today?",
        placeholder="e.g., Latest breakthroughs in LLMs, React 19 features, Gaza news...",
    )

    if st.button("Generate My Digest", type="primary") or user_question:
        if not username:
            st.error("Please enter a username in the sidebar first.")
        elif not user_question:
            st.warning("Please tell me what you'd like to learn about.")
        else:
            with st.spinner("🤖 Agent is researching and summarizing for you..."):
                try:
                    digest = call_digest_api(username, user_question)

                    st.divider()
                    st.subheader("✨ Your Daily Digest")
                    st.markdown(digest)

                    st.balloons()
                except requests.exceptions.RequestException as e:
                    st.error(f"API request failed: {e}")
                    st.info(
                        "Please ensure the backend API service is running. "
                        "You may need to start it with `docker-compose up`."
                    )
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")

    # Footer
    st.divider()
    st.caption("Powered by OpenAI, Arxiv, Hacker News, and The Guardian.")


if __name__ == "__main__":
    main()
