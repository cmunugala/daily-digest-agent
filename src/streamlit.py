from sqlmodel import Session, select

import streamlit as st
from agent import run_daily_digest_workflow
from database import engine, init_db
from models import Article, Interest, User

# Page config
st.set_page_config(page_title="Daily Digest Agent", page_icon="📰", layout="wide")

# Initialize database
init_db()


def main():
    st.title("📰 Daily Digest Agent")
    st.markdown("""
    Your personalized AI news assistant. Tell me what you're interested in today, 
    and I'll find the latest articles from Arxiv, Hacker News, and The Guardian.
    """)

    # Sidebar for User Profile
    with st.sidebar:
        st.header("User Profile")
        username = st.text_input("Enter your username", value="default_user")

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

    if st.button("Generate My Digest", type="primary"):
        if not username:
            st.error("Please enter a username in the sidebar first.")
        elif not user_question:
            st.warning("Please tell me what you'd like to learn about.")
        else:
            with st.spinner("🤖 Agent is researching and summarizing for you..."):
                try:
                    digest = run_daily_digest_workflow(username, user_question)

                    st.divider()
                    st.subheader("✨ Your Daily Digest")
                    st.markdown(digest)

                    st.balloons()
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.info("Check your API keys and database connection.")

    # Footer
    st.divider()
    st.caption("Powered by OpenAI, Arxiv, Hacker News, and The Guardian.")


if __name__ == "__main__":
    main()
