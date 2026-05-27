from pydantic import BaseModel


class BookingCategoryInsight(BaseModel):
    name: str
    count: int


class CustomerProfileInsights(BaseModel):
    saved_styles_count: int
    followed_salons_count: int
    recent_booking_categories: list[BookingCategoryInsight]


class FollowerGrowthInsight(BaseModel):
    total_followers: int
    last_30_days: int
    previous_30_days: int
    delta: int


class SalonProfileInsights(BaseModel):
    profile_views: int
    unique_profile_viewers: int
    service_taps: int
    booking_conversion_rate: float
    returning_customers: int
    follower_growth: FollowerGrowthInsight


class ProfileInsightsResponse(BaseModel):
    role: str
    customer: CustomerProfileInsights | None = None
    salon: SalonProfileInsights | None = None
