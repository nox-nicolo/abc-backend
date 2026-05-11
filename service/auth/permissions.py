from __future__ import annotations

from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.enumeration import AccountAccessStatus
from models.auth.user import User
from models.profile.salon import Salon, SalonStylist
from pydantic_schemas.auth.jwt_token import TokenData
from service.auth.JWT.oauth2 import get_current_user


ROLE_CUSTOMER = "customer"
ROLE_SALON_OWNER = "salon_owner"
ROLE_STYLIST = "stylist"
ROLE_ADMIN = "admin"

# Existing clients/database rows use `service` for salon owners. Keep it as
# a backwards-compatible alias while new permission code uses salon_owner.
_ROLE_ALIASES = {
    "service": ROLE_SALON_OWNER,
    "salon": ROLE_SALON_OWNER,
    "salon_owner": ROLE_SALON_OWNER,
    "owner": ROLE_SALON_OWNER,
    "stylist": ROLE_STYLIST,
    "admin": ROLE_ADMIN,
    "customer": ROLE_CUSTOMER,
    "user": ROLE_CUSTOMER,
    "": ROLE_CUSTOMER,
}


@dataclass(frozen=True)
class UserPrincipal:
    user_id: str
    role: str
    user: User


@dataclass(frozen=True)
class SalonPrincipal(UserPrincipal):
    salon_id: str
    salon: Salon


@dataclass(frozen=True)
class StylistPrincipal(UserPrincipal):
    stylist_id: str
    salon_id: str
    stylist: SalonStylist


def normalize_role(role: str | None) -> str:
    raw = (role or "").strip().lower()
    return _ROLE_ALIASES.get(raw, raw or ROLE_CUSTOMER)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _load_active_user(db: Session, current_user: TokenData) -> User:
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.account_access != AccountAccessStatus.ACTIVE:
        raise _forbidden("Account is not active")

    return user


def _principal_for(user: User) -> UserPrincipal:
    return UserPrincipal(user_id=user.id, role=normalize_role(user.role), user=user)


def require_active_user(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> UserPrincipal:
    return _principal_for(_load_active_user(db, current_user))


def require_admin(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> UserPrincipal:
    user = _load_active_user(db, current_user)
    principal = _principal_for(user)
    if principal.role != ROLE_ADMIN:
        raise _forbidden("Admin permission required")
    return principal


def require_salon_owner(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> SalonPrincipal:
    user = _load_active_user(db, current_user)
    salon = db.query(Salon).filter(Salon.user_id == user.id).first()
    if not salon:
        raise _forbidden("Salon owner permission required")

    return SalonPrincipal(
        user_id=user.id,
        role=ROLE_SALON_OWNER,
        user=user,
        salon_id=salon.id,
        salon=salon,
    )


def require_stylist(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> StylistPrincipal:
    user = _load_active_user(db, current_user)
    stylist = (
        db.query(SalonStylist)
        .filter(
            SalonStylist.user_id == user.id,
            SalonStylist.is_active == True,
        )
        .first()
    )
    if not stylist:
        raise _forbidden("Stylist permission required")

    return StylistPrincipal(
        user_id=user.id,
        role=ROLE_STYLIST,
        user=user,
        stylist_id=stylist.id,
        salon_id=stylist.salon_id,
        stylist=stylist,
    )


def require_any_role(*allowed_roles: str):
    normalized_allowed = {normalize_role(role) for role in allowed_roles}

    def dependency(
        principal: UserPrincipal = Depends(require_active_user),
    ) -> UserPrincipal:
        if principal.role not in normalized_allowed:
            allowed = ", ".join(sorted(normalized_allowed))
            raise _forbidden(f"One of these roles is required: {allowed}")
        return principal

    return dependency
