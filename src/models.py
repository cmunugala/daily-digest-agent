from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship


class UserArticleLink(SQLModel, table=True):
    """Junction table connecting Users and Articles to track 'Seen' history."""

    __table_args__ = {"extend_existing": True}

    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    article_id: Optional[int] = Field(
        default=None, foreign_key="article.id", primary_key=True
    )
    seen_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    interests: List["Interest"] = Relationship(back_populates="user")
    seen_articles: List["Article"] = Relationship(
        back_populates="viewed_by", link_model=UserArticleLink
    )


class Interest(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field()
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="interests")


class Article(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="No Title")
    url: Optional[str] = Field(default=None, unique=True, nullable=True)
    source: str
    viewed_by: List[User] = Relationship(
        back_populates="seen_articles", link_model=UserArticleLink
    )
