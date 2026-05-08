"""Import all SQLAlchemy models so Base.metadata is complete.

Alembic imports this module before reading metadata for autogenerate. Keep new
model modules listed here whenever new tables are added.
"""

import models.auth.customer_profile  # noqa: F401
import models.auth.profile_picture  # noqa: F401
import models.auth.refresh_token  # noqa: F401
import models.auth.user  # noqa: F401
import models.auth.verification  # noqa: F401
import models.booking.booking  # noqa: F401
import models.notifications.notification  # noqa: F401
import models.posts.posts  # noqa: F401
import models.profile.notification_preferences  # noqa: F401
import models.profile.salon  # noqa: F401
import models.profile.user  # noqa: F401
import models.search.search  # noqa: F401
import models.services.service  # noqa: F401
