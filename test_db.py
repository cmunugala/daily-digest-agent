from src.database import init_db, engine
from src.models import User
from sqlmodel import Session, select


def run_test():
    print("🚀 Connecting to Docker Postgres...")
    init_db()

    with Session(engine) as session:
        print("👤 Creating a test user...")
        test_user = User(name="AI Agent Explorer")
        session.add(test_user)
        session.commit()
        print(f"✅ Success! Saved user {test_user.name} with ID: {test_user.id}")


def check_for_user(target_name: str):
    with Session(engine) as session:
        # 1. Create a selection statement
        statement = select(User).where(User.name == target_name)

        # 2. Execute and get the first result
        results = session.exec(statement)
        user = results.first()

        if user:
            print(f"🔍 Found User: {user.name} (ID: {user.id})")
        else:
            print(f"❌ User '{target_name}' not found.")


if __name__ == "__main__":
    # run_test()
    check_for_user("AI Agent Explorer")
