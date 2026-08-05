"""Provides the Base database model module for the backend application."""

from sqlalchemy.ext.declarative import declarative_base

# for creating table if not exist in the database

Base = declarative_base()