from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Boolean, Enum, TIMESTAMP, VARCHAR, Float
from sqlalchemy.orm import relationship
from core.enumeration import PostVisibility, PostStatus, MediaType, MediaState, ReportReason, ReportStatus
from models.base import Base  
    

# -----------------------------------------------------------
# 1. MODEL: PostSettings
# -----------------------------------------------------------
class PostSettings(Base):
    __tablename__ = "post_settings"

    id = Column(String(36), primary_key=True, index=True)
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True)

    visibility = Column(Enum(PostVisibility), default=PostVisibility.PUBLIC, nullable=False)
    allow_comments = Column(Boolean, default=True)
    allow_likes = Column(Boolean, default=True)
    allow_share = Column(Boolean, default=True)
    is_pinned = Column(Boolean, default=False)
    location = Column(VARCHAR(255), nullable=True)

    age_restriction = Column(VARCHAR(50), default="Everyone", nullable=False)
    disable_reactions = Column(Boolean, default=False, nullable=False)

    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    post = relationship("Post", back_populates="settings")


    def __repr__(self):
        return f"<PostSettings post_id={self.post_id}, visibility={self.visibility}>"



# -----------------------------------------------------------
# 2. MODEL: Post
# -----------------------------------------------------------
class Post(Base):
    __tablename__ = "posts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    caption_text = Column(Text, nullable=True)

    status = Column(Enum(PostStatus), default=PostStatus.PUBLISHED, nullable=False)
    sub_service_id = Column(String(36), ForeignKey("sub_services.id"))
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="posts")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    shares = relationship("PostShare", back_populates="post", cascade="all, delete-orphan")
    sub_service = relationship("SubServices", back_populates="posts")
    reports = relationship("PostReport", back_populates="post", cascade="all, delete-orphan")
    media_items = relationship("MediaData", back_populates="post", cascade="all, delete-orphan")
    views = relationship("PostView", back_populates="post", cascade="all, delete-orphan")
    post_hashtags = relationship("PostHashtag", back_populates="post", cascade="all, delete-orphan")
    post_mentions = relationship("PostMention", back_populates="post", cascade="all, delete-orphan")
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False, cascade="all, delete-orphan")
    bookmarks = relationship("PostBoorkmark", back_populates="post", cascade="all, delete-orphan")
    settings = relationship("PostSettings", back_populates="post", uselist=False, cascade="all, delete-orphan")

    @property
    def sub_service_name(self):
        return self.sub_service.name if self.sub_service else None

    def __repr__(self):
        return f"<Post id={self.id}, user_id={self.user_id}, caption={self.caption_text[:20]}... , status={self.status}>"



# -----------------------------------------------------------
# 3. MODEL: MediaData
# -----------------------------------------------------------
class MediaData(Base):
    __tablename__ = "media_data"

    id = Column(String(36), primary_key=True, index=True)
    media_type = Column(Enum(MediaType), nullable=False)
    media_url = Column(Text, nullable=False)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    media_state = Column(Enum(MediaState), default=MediaState.UPLOADED, nullable=False)
    aspect_ratio = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)


    # Relationship with Post
    post = relationship("Post", back_populates="media_items", uselist=False)

    def __repr__(self):
        return f"<MediaData id={self.id}, post_id={self.post_id}, media_url={self.media_url}>"



# -----------------------------------------------------------
# 4. MODEL: PostBoorkmark (User bookmarks a Post)
# -----------------------------------------------------------
class PostBoorkmark(Base):
    # Table name
    __tablename__ = "post_bookmarks"
    
    # Columns
    id = Column(String(36), primary_key = True, index = True)  # Unique Bookmark ID
    user_id = Column(String(36), ForeignKey('users.id'), nullable = False)  # FK to User who bookmarked
    post_id = Column(String(36), ForeignKey('posts.id'), nullable = False)  # FK to bookmarked Post
    created_at = Column(TIMESTAMP, default = datetime.now(timezone.utc), nullable = False)  # When the bookmark was created
    
    # Relationships
    user = relationship("User", back_populates = "bookmarks")
    post = relationship("Post", back_populates = 'bookmarks')

    def __repr__(self):
        return f"<PostBoorkmark id={self.id}, user_id={self.user_id}, post_id={self.post_id}>"
    


# -----------------------------------------------------------
# 5. MODEL: PostAnalytics (Analytics for a Post)
# -----------------------------------------------------------
class PostAnalytics(Base):
    # Table name
    __tablename__ = "post_analytics"
    
    # Columns
    id = Column(String(36), primary_key=True, index=True)  # Unique Analytics ID
    post_id = Column(String(36), ForeignKey('posts.id'), nullable=False)  # Foreign Key to Post (metrics owner)
    reach_count = Column(Integer, default=0)  # Number of unique users who viewed the post
    engagement_score = Column(Integer, default=0)  # Engagement score based on likes, comments, shares
    impressions = Column(Integer, default=0)  # Total number of times the post was displayed
    updated_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)  # Timestamp of last update
    
    # Relationship with the Post
    post = relationship("Post", back_populates="analytics")

    def __repr__(self):
        return f"<PostAnalytics id={self.id}, post_id={self.post_id}, reach={self.reach_count}, engagement={self.engagement_score}>"
   


# -----------------------------------------------------------
# 6. MODEL: PostMention (Mentioned users in a Post)
# -----------------------------------------------------------
class PostMention(Base):
    # Table name
    __tablename__ = "post_mentions"
    
    # Columns
    id = Column(String(36), primary_key=True, index=True)  # Unique Mention ID
    post_id = Column(String(36), ForeignKey('posts.id', ondelete="CASCADE"), nullable=False)  # Foreign Key to Post
    mentioned_user_id = Column(String(36), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)  # Foreign Key to User (mentioned user)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)  # Timestamp of when the user was mentioned

    # Relationships
    post = relationship("Post", back_populates="post_mentions")  # Link back to Post
    mentioned_user = relationship("User", back_populates="mentions")  # Link back to User

    def __repr__(self):
        return f"<PostMention id={self.id}, post_id={self.post_id}, mentioned_user_id={self.mentioned_user_id}>"



# -----------------------------------------------------------
# 7. MODEL: PostHashtag (Hashtags linked to Posts)
# -----------------------------------------------------------
class PostHashtag(Base):
    # Table name
    __tablename__ = "post_hashtags"
    
    # Columns
    id = Column(String(36), primary_key=True, index=True)  # Unique Record ID
    post_id = Column(String(36), ForeignKey('posts.id', ondelete="CASCADE"), nullable=False)  # Foreign Key to Post
    hashtag_id = Column(String(36), ForeignKey('hashtags.id', ondelete="CASCADE"), nullable=False)  # Foreign Key to Hashtag
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)  # Timestamp of when the hashtag was added to the post

    # Relationships
    post = relationship("Post", back_populates="post_hashtags")  # Link back to Post
    hashtag = relationship("Hashtag", back_populates="post_hashtags")  # Link back to Hashtag

    def __repr__(self):
        return f"<PostHashtag id={self.id}, post_id={self.post_id}, hashtag_id={self.hashtag_id}>"



# -----------------------------------------------------------
# 8. MODEL: Hashtag (Hashtag definitions)
# -----------------------------------------------------------
class Hashtag(Base):
    # Table name
    __tablename__ = "hashtags"
    
    # Columns
    id = Column(String(36), primary_key=True, index=True)  # Unique Hashtag ID
    name = Column(String(100), unique=True, nullable=False, index=True)  # Hashtag name (lowercased)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)  # Timestamp of creation
    
    # Relationships
    post_hashtags = relationship("PostHashtag", back_populates="hashtag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Hashtag id={self.id}, name={self.name}>"
    
    
    
# -----------------------------------------------------------
# 9. MODEL: PostShare  ✅ FIXED
# -----------------------------------------------------------
class PostShare(Base):
    __tablename__ = "post_shares"

    id = Column(String(36), primary_key=True)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)

    share_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    post = relationship("Post", back_populates="shares")

    share_user = relationship(
        "User",
        back_populates="shared_posts",
        foreign_keys=[share_user_id],
    )

    user = relationship(
        "User",
        back_populates="received_shared_posts",
        foreign_keys=[user_id],
    )
    
    def __repr__(self):
        return f"<PostShare id={self.id}, post_id={self.post_id}, share_user_id={self.share_user_id}, user_id={self.user_id}>"



# -----------------------------------------------------------
# 10. MODEL: PostView
# -----------------------------------------------------------
class PostView(Base):
    __tablename__ = "post_views"

    id = Column(String(36), primary_key=True, index=True)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    viewer_ip = Column(VARCHAR(45), nullable=False)
    viewed_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="views")
    user = relationship("User", back_populates="views")
    
    def __repr__(self):
        return f"<PostView id={self.id}, post_id={self.post_id}, user_id={self.user_id}, viewer_ip={self.viewer_ip}>"
    


# -----------------------------------------------------------
# 11. MODEL: PostLike
# -----------------------------------------------------------
class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(String(36), primary_key=True, index=True)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    liked = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")

    def __repr__(self):
        return f"<PostLike id={self.id}, post_id={self.post_id}, user_id={self.user_id}, created_at={self.created_at}>"



# -----------------------------------------------------------
# 12. MODEL: PostComment
# -----------------------------------------------------------
class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(String(36), primary_key=True, index=True)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False, index=True)
    user_com = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_rep = Column(String(36), nullable=True, index=True)
    comment_id = Column(String(36), ForeignKey("post_comments.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent_comment = relationship(
        "PostComment",
        remote_side=[id],
        back_populates="replies",
        uselist=False,
    )
    replies = relationship(
        "PostComment",
        back_populates="parent_comment",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<PostComment id={self.id}, post_id={self.post_id}, user_id={self.user_id}, content={self.content[:20]}...>"



# -----------------------------------------------------------
# 13. MODEL: PostReport
# -----------------------------------------------------------
class PostReport(Base):
    __tablename__ = "post_reports"

    id = Column(String(36), primary_key=True, index=True)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reason = Column(Enum(ReportReason), default=ReportReason.INAPPROPRIATE, nullable=False)
    detail = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="reports")
    user = relationship("User", back_populates="reports")
    
    def __repr__(self):
        return f"<PostReport id={self.id}, post_id={self.post_id}, user_id={self.user_id}>"
    