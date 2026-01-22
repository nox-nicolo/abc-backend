

def calculate_salon_score(
    followers: int,
    posts: int,
    rating: float,
    completed_bookings: int,
    profile_completion: float,
) -> float:
    return (
        followers * 0.35 +
        posts * 0.15 +
        rating * 25 +
        completed_bookings * 0.2 +
        profile_completion * 15
    )
