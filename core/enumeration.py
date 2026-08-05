"""Provides the Enumeration shared infrastructure module for the backend application."""

from enum import Enum as PyEnum

ADDRESS = "http://192.168.43.160:8000"

# R2 Address for cloud storage, this is used to construct the image URLs for the profile and service images
# BASE_URL = "https://579664b4b8d25ad1f56fd28d4b85f706.eu.r2.cloudflarestorage.com/assets"

# code status for account verifications 
class Status(PyEnum):
    PENDING = "pending"
    FAILED = "failed"
    SUCCESS = "success"
    
    
# Account Status
class AccountAccessStatus(PyEnum):
    ACTIVE = "active" # active working [ full access]
    BANNED = "banned" # permanently restricted [ no access to the account] [ can be reached ]
    DELETED = "deleted" # permanent deleted or marked remove [ no access to the account, no reachable]
    LOCKED = "locked"   # temporary locked, suspecious activities [ No access until unlocked]
    PENDING = "pending" # limited or no access, verification issue [ no access until verified]
    SUSPENDED = "suspended" # temporarily resticted due to violations, payments issues or manual actions. [ limited access]
    

# Post
# This is used to store the post collection type
class PostCollectionType(PyEnum):
    feed = "feed"
    # profile = "profile"
    explore = "explore"
    saved = "saved"
    trending = "trending"
    
# This is used to store the post status and visibility
# Media type and state for the post
class PostVisibility(PyEnum):
    PUBLIC = "Public"  # Visible to everyone
    FRIENDS = "Friends"  # Visible to friends only
    PRIVATE = "Private"  # Visible to the user only
    
    
class PostStatus(PyEnum):
    PUBLISHED = "published"  # Active post
    FLAGGED = "flagged"  # Flagged post (for sensitive content)
    DELETED = "deleted"  # Deleted post
    DRAFT = "draft"  # Draft post (not published yet)  
    ARCHIVED = "archived"  # Archived post (not visible to others)
    
    
class MediaType(PyEnum):
    IMAGE = "image"  # Image file
    VIDEO = "video"  # Video file
    GIF = "gif"  # GIF file    
    MIXED = 'mixed' 
    

class MediaState(PyEnum):
    UPLOADED = "uploaded"  # Media has been uploaded
    PROCESSING = "processing"  # Media is being processed
    FAILED = "failed"  # Media processing failed
    PROCESSED = "processed"  # Media has been processed successfully
    DELETED = "deleted"  # Media has been deleted


class AdPlacement(PyEnum):
    HOME_FEED = "home_feed"
    SEARCH = "search"
    POST_VIEW = "post_view"


class AdStatus(PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    
    

# Image URL and Directory
class ImageDirectories(PyEnum):
    PROFILE_DIR = "assets/images/user_profile_picture/"
    SERVICE_DIR = "assets/images/service_list_styles/"
    POST_DIR = "assets/images/post/"
    SALON_COVER_DIR = "assets/images/salon_cover_photos/"
    SALON_GALLERY_DIR = "assets/images/salon_gallery/"
    
# # Version for cloud services,
# For cloud R2 storage, the URL is stored in the environment variable and accessed through the ImageURL enum

class ImageDirectories(PyEnum):
    PROFILE_DIR = "images/user_profile_picture/"
    SERVICE_DIR = "images/service_list_styles/"
    POST_DIR = "images/post/"
    SALON_COVER_DIR = "images/salon_cover_photos/"
    SALON_GALLERY_DIR = "images/salon_gallery/"

 
# No version for cloud services  
# This is used to store the image URL and directory for the profile and service images
class ImageURL(PyEnum):
    PROFILE_URL = f"{ADDRESS}/{ImageDirectories.PROFILE_DIR.value}"
    SERVICE_URL = f"{ADDRESS}/{ImageDirectories.SERVICE_DIR.value}"
    POSTS_URL = f"{ADDRESS}/{ImageDirectories.POST_DIR.value}"
    SALON_COVER_URL = f"{ADDRESS}/{ImageDirectories.SALON_COVER_DIR.value}"
    SALON_GALLERY_URL = f"{ADDRESS}/{ImageDirectories.SALON_GALLERY_DIR.value}"
 
    
# Report Isssue
class ReportStatus(PyEnum):
    PENDING = "pending"  
    REVIEWED = "reviewed"  
    RESOLVED = "resolved" 
    REJECTED = "rejected"  
    ESCALATED = "escalated"  
    
    
class ReportReason(PyEnum):
    SPAM = 'spam'
    INAPPROPRIATE = 'inappropriate'
    HARASSMENT = 'harassment'
    MISSINFORMATION = 'misinformation'
    OTHER = 'other'
    
    

class BookingStatus(PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    REJECTED = "rejected"  # Salon declined the request
    CANCELLED = "cancelled"
    EXPIRED = "expired"  # Salon did not confirm before the appointment time
    NO_SHOW = "no_show"  # Optional later Customer didn’t come
    
class ServiceCreatedStatus(PyEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'
