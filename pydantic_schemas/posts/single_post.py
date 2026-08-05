"""Provides the Single Post request and response schema module for posts workflows."""

from pydantic import BaseModel
from typing import List, Optional

from pydantic_schemas.posts.get_post import PostResponseSchema


# Service Context
class PriceRange(BaseModel):
    min: Optional[int]
    max: Optional[int]
    currency: str


class ServiceProduct(BaseModel):
    name: str
    brand: Optional[str]


class ServiceSection(BaseModel):
    id: str
    subname: str
    name: str
    price: PriceRange
    duration_minutes: Optional[int]
    benefits: List[str]
    products: List[ServiceProduct]


# Stylists
class StylistSection(BaseModel):
    id: str
    name: str
    avatar: Optional[str]
    title: Optional[str]
    rating: Optional[float]


# REview
class ReviewItem(BaseModel):
    id: str
    user_name: str
    user_avatar: Optional[str]
    rating: int
    comment: Optional[str]
    created_at: str


class ReviewSection(BaseModel):
    count: int
    average: Optional[float]
    items: List[ReviewItem]


# Similar Result
class PostPreview(BaseModel):
    id: str
    cover_image: str
    salon_name: Optional[str] = None
    salon_id: Optional[str] = None


class SimilarSection(BaseModel):
    items: List[PostPreview]


# Sponsored Salon
class SponsoredSalonSection(BaseModel):
    salon_id: str
    name: str
    image_url: Optional[str] = None
    location: Optional[str]
    rating: Optional[float]
    price: Optional[float]
    currency: str
    plan_type: str


#   Engagement State
class EngagementState(BaseModel):
    liked: bool
    saved: bool
    can_comment: bool
    can_share: bool
    can_react: bool
    my_reaction: Optional[str] = None


#   Booking State
class BookingState(BaseModel):
    can_book: bool
    has_booked_before: bool
    can_review: bool
    
    
# Other Posts (Exploration Feed)
class OtherPostsSection(BaseModel):
    items: List[PostResponseSchema]
    next_cursor: Optional[str] = None


#   Single Post Response
class SinglePostResponse(BaseModel):
    post: "PostResponseSchema"
    service: "ServiceSection"
    engagement: "EngagementState"
    booking: "BookingState"
    
    stylists: List["StylistSection"]
    reviews: "ReviewSection"
    similar: "SimilarSection"
    
    sponsored_salons: List["SponsoredSalonSection"]

    other_posts: "OtherPostsSection" 



SinglePostResponse.model_rebuild()
