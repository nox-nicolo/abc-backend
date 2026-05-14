"""initial schema

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260512_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('hashtags',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_hashtags_id'), 'hashtags', ['id'], unique=False)

    op.create_index(op.f('ix_hashtags_name'), 'hashtags', ['name'], unique=True)

    op.create_table('services',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('service_picture', sa.String(), nullable=False),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('rated', sa.FLOAT(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)

    op.create_index(op.f('ix_services_name'), 'services', ['name'], unique=True)

    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('password', sa.LargeBinary(), nullable=False),
    sa.Column('role', sa.String(), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.Column('account_access', sa.Enum('ACTIVE', 'BANNED', 'DELETED', 'LOCKED', 'PENDING', 'SUSPENDED', name='accountaccessstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_index('ix_users_name', 'users', ['name'], unique=False)

    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)

    op.create_index('ix_users_role_access_created', 'users', ['role', 'account_access', 'created_at'], unique=False)

    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table('customer_profiles',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('gender', sa.String(length=20), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_customer_profiles_user_id'), 'customer_profiles', ['user_id'], unique=True)

    op.create_table('profile_pictures',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('is_custom', sa.Boolean(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_profile_pictures_id'), 'profile_pictures', ['id'], unique=False)

    op.create_index(op.f('ix_profile_pictures_user_id'), 'profile_pictures', ['user_id'], unique=True)

    op.create_table('refresh_tokens',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token', sa.String(length=512), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)

    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    op.create_table('salons',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('slogan', sa.String(length=300), nullable=True),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('display_ads', sa.String(length=200), nullable=True),
    sa.Column('profile_completion', sa.FLOAT(), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salons_id'), 'salons', ['id'], unique=False)

    op.create_index(op.f('ix_salons_user_id'), 'salons', ['user_id'], unique=False)

    op.create_table('search_histories',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('query', sa.String(length=255), nullable=False),
    sa.Column('entity', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_search_histories_entity_entity_id', 'search_histories', ['entity', 'entity_id'], unique=False)

    op.create_index(op.f('ix_search_histories_id'), 'search_histories', ['id'], unique=False)

    op.create_index('ix_search_histories_user_created', 'search_histories', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_search_histories_user_id'), 'search_histories', ['user_id'], unique=False)

    op.create_index('ix_search_histories_user_query', 'search_histories', ['user_id', 'query'], unique=False)

    op.create_table('sub_services',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('service_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('file_name', sa.String(), nullable=True),
    sa.Column('description', sa.TEXT(), nullable=True),
    sa.Column('rated', sa.FLOAT(), nullable=True),
    sa.Column('is_event', sa.BOOLEAN(), nullable=False),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service_id', 'name', name='uq_service_subservice')
    )

    op.create_index(op.f('ix_sub_services_id'), 'sub_services', ['id'], unique=False)

    op.create_index(op.f('ix_sub_services_name'), 'sub_services', ['name'], unique=False)

    op.create_table('user_device_tokens',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('device_id', sa.String(length=120), nullable=False),
    sa.Column('platform', sa.String(length=30), nullable=False),
    sa.Column('push_provider', sa.String(length=30), nullable=False),
    sa.Column('push_token', sa.String(length=512), nullable=False),
    sa.Column('app_version', sa.String(length=80), nullable=True),
    sa.Column('build_number', sa.String(length=80), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'device_id', name='uq_user_device_tokens_user_device')
    )

    op.create_index('ix_user_device_tokens_token', 'user_device_tokens', ['push_token'], unique=False)

    op.create_index('ix_user_device_tokens_user_active', 'user_device_tokens', ['user_id', 'is_active'], unique=False)

    op.create_index(op.f('ix_user_device_tokens_user_id'), 'user_device_tokens', ['user_id'], unique=False)

    op.create_table('user_mutes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('target_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_user_mute_target')
    )

    op.create_index(op.f('ix_user_mutes_target_id'), 'user_mutes', ['target_id'], unique=False)

    op.create_index(op.f('ix_user_mutes_target_type'), 'user_mutes', ['target_type'], unique=False)

    op.create_index(op.f('ix_user_mutes_user_id'), 'user_mutes', ['user_id'], unique=False)

    op.create_index('ix_user_mutes_user_type_created', 'user_mutes', ['user_id', 'target_type', 'created_at'], unique=False)

    op.create_table('user_notification_preferences',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('allow_likes', sa.BOOLEAN(), nullable=False),
    sa.Column('allow_comments', sa.BOOLEAN(), nullable=False),
    sa.Column('allow_bookings', sa.BOOLEAN(), nullable=False),
    sa.Column('allow_promotions', sa.BOOLEAN(), nullable=False),
    sa.Column('allow_reminders', sa.BOOLEAN(), nullable=False),
    sa.Column('reminder_lead_minutes', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_user_notification_preferences_user_id'), 'user_notification_preferences', ['user_id'], unique=True)

    op.create_table('user_select_services',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('services', sa.ARRAY(sa.String()), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_user_select_services_id'), 'user_select_services', ['id'], unique=False)

    op.create_index(op.f('ix_user_select_services_user_id'), 'user_select_services', ['user_id'], unique=False)

    op.create_table('verifications',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('via', sa.String(length=20), nullable=False),
    sa.Column('code', sa.String(length=128), nullable=False),
    sa.Column('token', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('phone_verified', sa.Boolean(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'FAILED', 'SUCCESS', name='status'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_verifications_id'), 'verifications', ['id'], unique=False)

    op.create_index(op.f('ix_verifications_token'), 'verifications', ['token'], unique=True)

    op.create_table('billing_subscriptions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('plan_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('provider', sa.String(length=50), nullable=True),
    sa.Column('provider_ref', sa.String(length=100), nullable=True),
    sa.Column('start_at', sa.DateTime(), nullable=False),
    sa.Column('end_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_billing_subscriptions_id'), 'billing_subscriptions', ['id'], unique=False)

    op.create_index(op.f('ix_billing_subscriptions_salon_id'), 'billing_subscriptions', ['salon_id'], unique=False)

    op.create_table('chat_conversations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('salon_user_id', sa.String(length=36), nullable=False),
    sa.Column('last_message_preview', sa.String(length=500), nullable=True),
    sa.Column('last_message_type', sa.String(length=40), nullable=True),
    sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('customer_unread_count', sa.Integer(), nullable=False),
    sa.Column('salon_unread_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('customer_id', 'salon_id', name='uq_chat_customer_salon')
    )

    op.create_index(op.f('ix_chat_conversations_customer_id'), 'chat_conversations', ['customer_id'], unique=False)

    op.create_index('ix_chat_conversations_customer_last', 'chat_conversations', ['customer_id', 'last_message_at'], unique=False)

    op.create_index(op.f('ix_chat_conversations_id'), 'chat_conversations', ['id'], unique=False)

    op.create_index(op.f('ix_chat_conversations_last_message_at'), 'chat_conversations', ['last_message_at'], unique=False)

    op.create_index(op.f('ix_chat_conversations_salon_id'), 'chat_conversations', ['salon_id'], unique=False)

    op.create_index(op.f('ix_chat_conversations_salon_user_id'), 'chat_conversations', ['salon_user_id'], unique=False)

    op.create_index('ix_chat_conversations_salon_user_last', 'chat_conversations', ['salon_user_id', 'last_message_at'], unique=False)

    op.create_table('posts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('caption_text', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PUBLISHED', 'FLAGGED', 'DELETED', 'DRAFT', 'ARCHIVED', name='poststatus'), nullable=False),
    sa.Column('post_type', sa.String(length=30), nullable=False),
    sa.Column('sub_service_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['sub_service_id'], ['sub_services.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_posts_id'), 'posts', ['id'], unique=False)

    op.create_index(op.f('ix_posts_post_type'), 'posts', ['post_type'], unique=False)

    op.create_index('ix_posts_status_created', 'posts', ['status', 'created_at'], unique=False)

    op.create_index('ix_posts_sub_service_created', 'posts', ['sub_service_id', 'created_at'], unique=False)

    op.create_index('ix_posts_type_created', 'posts', ['post_type', 'created_at'], unique=False)

    op.create_index('ix_posts_user_created', 'posts', ['user_id', 'created_at'], unique=False)

    op.create_table('rated',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('value', sa.INTEGER(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'salon_id', name='uq_user_salon_rating')
    )

    op.create_index(op.f('ix_rated_id'), 'rated', ['id'], unique=False)

    op.create_table('salon_availability_overrides',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('date', sa.DATE(), nullable=False),
    sa.Column('is_closed', sa.BOOLEAN(), nullable=False),
    sa.Column('open_time', sa.TIME(), nullable=True),
    sa.Column('close_time', sa.TIME(), nullable=True),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'date', name='uq_salon_availability_override_date')
    )

    op.create_index(op.f('ix_salon_availability_overrides_date'), 'salon_availability_overrides', ['date'], unique=False)

    op.create_index('ix_salon_availability_overrides_salon_date', 'salon_availability_overrides', ['salon_id', 'date'], unique=False)

    op.create_index(op.f('ix_salon_availability_overrides_salon_id'), 'salon_availability_overrides', ['salon_id'], unique=False)

    op.create_table('salon_blocks',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'user_id', name='uq_user_block_salon')
    )

    op.create_index(op.f('ix_salon_blocks_id'), 'salon_blocks', ['id'], unique=False)

    op.create_index('ix_salon_blocks_salon_created', 'salon_blocks', ['salon_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_blocks_salon_id'), 'salon_blocks', ['salon_id'], unique=False)

    op.create_index('ix_salon_blocks_user_created', 'salon_blocks', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_blocks_user_id'), 'salon_blocks', ['user_id'], unique=False)

    op.create_table('salon_contacts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.Column('is_primary', sa.BOOLEAN(), nullable=False),
    sa.Column('is_verified', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_contacts_id'), 'salon_contacts', ['id'], unique=False)

    op.create_index(op.f('ix_salon_contacts_salon_id'), 'salon_contacts', ['salon_id'], unique=False)

    op.create_index('uq_primary_contact_per_type', 'salon_contacts', ['salon_id', 'type'], unique=True, postgresql_where=sa.text('is_primary = true'))

    op.create_table('salon_followers',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('notifications_enabled', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'user_id', name='uq_salon_user_follow')
    )

    op.create_index(op.f('ix_salon_followers_id'), 'salon_followers', ['id'], unique=False)

    op.create_index('ix_salon_followers_notifications', 'salon_followers', ['salon_id', 'notifications_enabled'], unique=False)

    op.create_index('ix_salon_followers_salon_created', 'salon_followers', ['salon_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_followers_salon_id'), 'salon_followers', ['salon_id'], unique=False)

    op.create_index('ix_salon_followers_user_created', 'salon_followers', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_followers_user_id'), 'salon_followers', ['user_id'], unique=False)

    op.create_table('salon_galleries',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('file_name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_galleries_id'), 'salon_galleries', ['id'], unique=False)

    op.create_table('salon_locations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('region', sa.String(length=100), nullable=True),
    sa.Column('street', sa.String(length=200), nullable=True),
    sa.Column('latitude', sa.FLOAT(), nullable=True),
    sa.Column('longitude', sa.FLOAT(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_locations_salon_id'), 'salon_locations', ['salon_id'], unique=True)

    op.create_table('salon_reports',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'user_id', name='uq_user_report_salon')
    )

    op.create_index(op.f('ix_salon_reports_id'), 'salon_reports', ['id'], unique=False)

    op.create_index('ix_salon_reports_salon_created', 'salon_reports', ['salon_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_reports_salon_id'), 'salon_reports', ['salon_id'], unique=False)

    op.create_index('ix_salon_reports_user_created', 'salon_reports', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_salon_reports_user_id'), 'salon_reports', ['user_id'], unique=False)

    op.create_table('salon_service_prices',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('service_id', sa.String(length=36), nullable=True),
    sa.Column('sub_service_id', sa.String(length=36), nullable=True),
    sa.Column('price_min', sa.INTEGER(), nullable=True),
    sa.Column('price_max', sa.INTEGER(), nullable=True),
    sa.Column('currency', sa.String(length=10), nullable=True),
    sa.Column('duration_minutes', sa.INTEGER(), nullable=True),
    sa.Column('concurrent_capacity', sa.INTEGER(), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ARCHIVED', name='servicecreatedstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('(service_id IS NOT NULL OR sub_service_id IS NOT NULL)', name='ck_service_or_subservice_required'),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sub_service_id'], ['sub_services.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_service_prices_id'), 'salon_service_prices', ['id'], unique=False)

    op.create_index(op.f('ix_salon_service_prices_salon_id'), 'salon_service_prices', ['salon_id'], unique=False)

    op.create_index(op.f('ix_salon_service_prices_status'), 'salon_service_prices', ['status'], unique=False)

    op.create_index('ix_service_lookup', 'salon_service_prices', ['salon_id', 'service_id', 'sub_service_id'], unique=False)

    op.create_table('salon_stylists',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=True),
    sa.Column('bio', sa.String(length=500), nullable=True),
    sa.Column('is_owner', sa.BOOLEAN(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'user_id', name='uq_salon_stylist')
    )

    op.create_index(op.f('ix_salon_stylists_id'), 'salon_stylists', ['id'], unique=False)

    op.create_index(op.f('ix_salon_stylists_salon_id'), 'salon_stylists', ['salon_id'], unique=False)

    op.create_index(op.f('ix_salon_stylists_user_id'), 'salon_stylists', ['user_id'], unique=False)

    op.create_table('salon_working_hours',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('day_of_week', sa.INTEGER(), nullable=False),
    sa.Column('is_open', sa.BOOLEAN(), nullable=False),
    sa.Column('open_time', sa.TIME(), nullable=True),
    sa.Column('close_time', sa.TIME(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('salon_id', 'day_of_week', name='uq_salon_day')
    )

    op.create_index(op.f('ix_salon_working_hours_salon_id'), 'salon_working_hours', ['salon_id'], unique=False)

    op.create_table('saved_salons',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'salon_id', name='uq_saved_salons_user_salon')
    )

    op.create_index(op.f('ix_saved_salons_id'), 'saved_salons', ['id'], unique=False)

    op.create_index('ix_saved_salons_salon_created', 'saved_salons', ['salon_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_salons_salon_id'), 'saved_salons', ['salon_id'], unique=False)

    op.create_index('ix_saved_salons_user_created', 'saved_salons', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_salons_user_id'), 'saved_salons', ['user_id'], unique=False)

    op.create_table('sponsored_salons',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('plan_type', sa.String(length=50), nullable=False),
    sa.Column('start_at', sa.DateTime(), nullable=False),
    sa.Column('end_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), nullable=False),
    sa.Column('priority', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_active_sponsored_salon', 'sponsored_salons', ['plan_type', 'is_active', 'start_at', 'end_at'], unique=False)

    op.create_index(op.f('ix_sponsored_salons_end_at'), 'sponsored_salons', ['end_at'], unique=False)

    op.create_index(op.f('ix_sponsored_salons_id'), 'sponsored_salons', ['id'], unique=False)

    op.create_index(op.f('ix_sponsored_salons_is_active'), 'sponsored_salons', ['is_active'], unique=False)

    op.create_index(op.f('ix_sponsored_salons_plan_type'), 'sponsored_salons', ['plan_type'], unique=False)

    op.create_index(op.f('ix_sponsored_salons_salon_id'), 'sponsored_salons', ['salon_id'], unique=True)

    op.create_index(op.f('ix_sponsored_salons_start_at'), 'sponsored_salons', ['start_at'], unique=False)

    op.create_table('bookings',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=True),
    sa.Column('start_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('end_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'NO_SHOW', name='bookingstatus'), nullable=False),
    sa.Column('service_name_snapshot', sa.String(length=120), nullable=True),
    sa.Column('price_snapshot', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency_snapshot', sa.String(length=10), nullable=False),
    sa.Column('duration_minutes_snapshot', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('cancelled_by', sa.String(length=10), nullable=True),
    sa.Column('cancel_reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_bookings_created', 'bookings', ['created_at'], unique=False)

    op.create_index(op.f('ix_bookings_customer_id'), 'bookings', ['customer_id'], unique=False)

    op.create_index('ix_bookings_customer_start', 'bookings', ['customer_id', 'start_at'], unique=False)

    op.create_index('ix_bookings_customer_status_start', 'bookings', ['customer_id', 'status', 'start_at'], unique=False)

    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)

    op.create_index(op.f('ix_bookings_salon_id'), 'bookings', ['salon_id'], unique=False)

    op.create_index(op.f('ix_bookings_salon_service_price_id'), 'bookings', ['salon_service_price_id'], unique=False)

    op.create_index('ix_bookings_salon_start', 'bookings', ['salon_id', 'start_at'], unique=False)

    op.create_index('ix_bookings_salon_status_start', 'bookings', ['salon_id', 'status', 'start_at'], unique=False)

    op.create_index('ix_bookings_service_status_start', 'bookings', ['salon_service_price_id', 'status', 'start_at'], unique=False)

    op.create_index(op.f('ix_bookings_start_at'), 'bookings', ['start_at'], unique=False)

    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)

    op.create_table('media_data',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('media_type', sa.Enum('IMAGE', 'VIDEO', 'GIF', 'MIXED', name='mediatype'), nullable=False),
    sa.Column('media_url', sa.Text(), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('media_state', sa.Enum('UPLOADED', 'PROCESSING', 'FAILED', 'PROCESSED', 'DELETED', name='mediastate'), nullable=False),
    sa.Column('aspect_ratio', sa.Float(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_media_data_id'), 'media_data', ['id'], unique=False)

    op.create_index('ix_media_data_post_created', 'media_data', ['post_id', 'created_at'], unique=False)

    op.create_table('post_analytics',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('reach_count', sa.Integer(), nullable=True),
    sa.Column('engagement_score', sa.Integer(), nullable=True),
    sa.Column('impressions', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_analytics_id'), 'post_analytics', ['id'], unique=False)

    op.create_table('post_bookmarks',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_bookmarks_id'), 'post_bookmarks', ['id'], unique=False)

    op.create_index('ix_post_bookmarks_user_created', 'post_bookmarks', ['user_id', 'created_at'], unique=False)

    op.create_index('ix_post_bookmarks_user_post', 'post_bookmarks', ['user_id', 'post_id'], unique=False)

    op.create_table('post_comments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('user_com', sa.String(length=36), nullable=False),
    sa.Column('user_rep', sa.String(length=36), nullable=True),
    sa.Column('comment_id', sa.String(length=36), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['comment_id'], ['post_comments.id'], ),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_com'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_comments_comment_id'), 'post_comments', ['comment_id'], unique=False)

    op.create_index(op.f('ix_post_comments_id'), 'post_comments', ['id'], unique=False)

    op.create_index(op.f('ix_post_comments_post_id'), 'post_comments', ['post_id'], unique=False)

    op.create_index('ix_post_comments_post_parent_created', 'post_comments', ['post_id', 'comment_id', 'created_at'], unique=False)

    op.create_index('ix_post_comments_user_created', 'post_comments', ['user_com', 'created_at'], unique=False)

    op.create_index(op.f('ix_post_comments_user_rep'), 'post_comments', ['user_rep'], unique=False)

    op.create_table('post_hashtags',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('hashtag_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['hashtag_id'], ['hashtags.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_post_hashtags_hashtag_created', 'post_hashtags', ['hashtag_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_post_hashtags_id'), 'post_hashtags', ['id'], unique=False)

    op.create_index('ix_post_hashtags_post_hashtag', 'post_hashtags', ['post_id', 'hashtag_id'], unique=False)

    op.create_table('post_likes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('liked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_likes_id'), 'post_likes', ['id'], unique=False)

    op.create_index('ix_post_likes_post_liked', 'post_likes', ['post_id', 'liked'], unique=False)

    op.create_index('ix_post_likes_post_user', 'post_likes', ['post_id', 'user_id'], unique=False)

    op.create_index('ix_post_likes_user_created', 'post_likes', ['user_id', 'created_at'], unique=False)

    op.create_table('post_mentions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('mentioned_user_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_mentions_id'), 'post_mentions', ['id'], unique=False)

    op.create_index('ix_post_mentions_mentioned_created', 'post_mentions', ['mentioned_user_id', 'created_at'], unique=False)

    op.create_index('ix_post_mentions_post_mentioned', 'post_mentions', ['post_id', 'mentioned_user_id'], unique=False)

    op.create_table('post_reports',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('reason', sa.Enum('SPAM', 'INAPPROPRIATE', 'HARASSMENT', 'MISSINFORMATION', 'OTHER', name='reportreason'), nullable=False),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'REVIEWED', 'RESOLVED', 'REJECTED', 'ESCALATED', name='reportstatus'), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('resolved_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_reports_id'), 'post_reports', ['id'], unique=False)

    op.create_index('ix_post_reports_post_status', 'post_reports', ['post_id', 'status'], unique=False)

    op.create_index('ix_post_reports_user_created', 'post_reports', ['user_id', 'created_at'], unique=False)

    op.create_table('post_settings',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('visibility', sa.Enum('PUBLIC', 'FRIENDS', 'PRIVATE', name='postvisibility'), nullable=False),
    sa.Column('allow_comments', sa.Boolean(), nullable=True),
    sa.Column('allow_likes', sa.Boolean(), nullable=True),
    sa.Column('allow_share', sa.Boolean(), nullable=True),
    sa.Column('is_pinned', sa.Boolean(), nullable=True),
    sa.Column('location', sa.VARCHAR(length=255), nullable=True),
    sa.Column('age_restriction', sa.VARCHAR(length=50), nullable=False),
    sa.Column('disable_reactions', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id')
    )

    op.create_index(op.f('ix_post_settings_id'), 'post_settings', ['id'], unique=False)

    op.create_table('post_shares',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('share_user_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['share_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_post_shares_post_created_user', 'post_shares', ['post_id', 'share_user_id'], unique=False)

    op.create_index('ix_post_shares_received_user', 'post_shares', ['user_id'], unique=False)

    op.create_index('ix_post_shares_share_user', 'post_shares', ['share_user_id'], unique=False)

    op.create_table('post_views',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('post_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('viewer_ip', sa.VARCHAR(length=45), nullable=False),
    sa.Column('viewed_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_post_views_id'), 'post_views', ['id'], unique=False)

    op.create_index('ix_post_views_post_viewed', 'post_views', ['post_id', 'viewed_at'], unique=False)

    op.create_index('ix_post_views_user_viewed', 'post_views', ['user_id', 'viewed_at'], unique=False)

    op.create_table('salon_service_benefits',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=False),
    sa.Column('benefit', sa.String(length=500), nullable=False),
    sa.Column('position', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_service_benefits_id'), 'salon_service_benefits', ['id'], unique=False)

    op.create_index(op.f('ix_salon_service_benefits_salon_service_price_id'), 'salon_service_benefits', ['salon_service_price_id'], unique=False)

    op.create_table('salon_service_products',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=False),
    sa.Column('product_name', sa.String(length=255), nullable=False),
    sa.Column('brand', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_salon_service_products_id'), 'salon_service_products', ['id'], unique=False)

    op.create_index(op.f('ix_salon_service_products_salon_service_price_id'), 'salon_service_products', ['salon_service_price_id'], unique=False)

    op.create_table('saved_services',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('service_id', sa.String(length=36), nullable=True),
    sa.Column('sub_service_id', sa.String(length=36), nullable=True),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sub_service_id'], ['sub_services.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'salon_service_price_id', name='uq_saved_services_user_salon_price'),
    sa.UniqueConstraint('user_id', 'service_id', name='uq_saved_services_user_service'),
    sa.UniqueConstraint('user_id', 'sub_service_id', name='uq_saved_services_user_sub_service')
    )

    op.create_index(op.f('ix_saved_services_id'), 'saved_services', ['id'], unique=False)

    op.create_index('ix_saved_services_salon_price_created', 'saved_services', ['salon_service_price_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_services_salon_service_price_id'), 'saved_services', ['salon_service_price_id'], unique=False)

    op.create_index('ix_saved_services_service_created', 'saved_services', ['service_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_services_service_id'), 'saved_services', ['service_id'], unique=False)

    op.create_index('ix_saved_services_sub_service_created', 'saved_services', ['sub_service_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_services_sub_service_id'), 'saved_services', ['sub_service_id'], unique=False)

    op.create_index('ix_saved_services_user_created', 'saved_services', ['user_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_saved_services_user_id'), 'saved_services', ['user_id'], unique=False)

    op.create_table('stylist_ratings',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('stylist_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('value', sa.INTEGER(), nullable=False),
    sa.Column('comment', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['stylist_id'], ['salon_stylists.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stylist_id', 'user_id', name='uq_user_stylist_rating')
    )

    op.create_index(op.f('ix_stylist_ratings_id'), 'stylist_ratings', ['id'], unique=False)

    op.create_index(op.f('ix_stylist_ratings_stylist_id'), 'stylist_ratings', ['stylist_id'], unique=False)

    op.create_index(op.f('ix_stylist_ratings_user_id'), 'stylist_ratings', ['user_id'], unique=False)

    op.create_table('stylist_services',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('stylist_id', sa.String(length=36), nullable=False),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stylist_id'], ['salon_stylists.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stylist_id', 'salon_service_price_id', name='uq_stylist_service')
    )

    op.create_index(op.f('ix_stylist_services_id'), 'stylist_services', ['id'], unique=False)

    op.create_index(op.f('ix_stylist_services_salon_service_price_id'), 'stylist_services', ['salon_service_price_id'], unique=False)

    op.create_index(op.f('ix_stylist_services_stylist_id'), 'stylist_services', ['stylist_id'], unique=False)

    op.create_table('chat_messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('sender_user_id', sa.String(length=36), nullable=True),
    sa.Column('sender_role', sa.String(length=20), nullable=False),
    sa.Column('message_type', sa.String(length=40), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('booking_id', sa.String(length=36), nullable=True),
    sa.Column('created_by_system', sa.Boolean(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_chat_messages_booking_id'), 'chat_messages', ['booking_id'], unique=False)

    op.create_index('ix_chat_messages_conversation_created', 'chat_messages', ['conversation_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)

    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)

    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

    op.create_index(op.f('ix_chat_messages_sender_user_id'), 'chat_messages', ['sender_user_id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('recipient_id', sa.String(length=36), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('post_id', sa.String(length=36), nullable=True),
    sa.Column('comment_id', sa.String(length=36), nullable=True),
    sa.Column('booking_id', sa.String(length=36), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('delivery_status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['comment_id'], ['post_comments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_notifications_actor_created', 'notifications', ['actor_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_notifications_booking_id'), 'notifications', ['booking_id'], unique=False)

    op.create_index(op.f('ix_notifications_delivery_status'), 'notifications', ['delivery_status'], unique=False)

    op.create_index(op.f('ix_notifications_post_id'), 'notifications', ['post_id'], unique=False)

    op.create_index('ix_notifications_recipient_created', 'notifications', ['recipient_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_notifications_recipient_id'), 'notifications', ['recipient_id'], unique=False)

    op.create_index('ix_notifications_recipient_read_created', 'notifications', ['recipient_id', 'is_read', 'created_at'], unique=False)

    op.create_index('ix_notifications_recipient_status_created', 'notifications', ['recipient_id', 'delivery_status', 'created_at'], unique=False)

    op.create_index('ix_notifications_recipient_unread', 'notifications', ['recipient_id', 'is_read'], unique=False)

    op.create_table('service_reviews',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('booking_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('salon_id', sa.String(length=36), nullable=False),
    sa.Column('salon_service_price_id', sa.String(length=36), nullable=False),
    sa.Column('stylist_id', sa.String(length=36), nullable=True),
    sa.Column('rating', sa.INTEGER(), nullable=False),
    sa.Column('comment', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['salon_service_price_id'], ['salon_service_prices.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stylist_id'], ['salon_stylists.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_service_reviews_booking_id'), 'service_reviews', ['booking_id'], unique=True)

    op.create_index(op.f('ix_service_reviews_id'), 'service_reviews', ['id'], unique=False)

    op.create_index(op.f('ix_service_reviews_salon_id'), 'service_reviews', ['salon_id'], unique=False)

    op.create_index(op.f('ix_service_reviews_salon_service_price_id'), 'service_reviews', ['salon_service_price_id'], unique=False)

    op.create_index(op.f('ix_service_reviews_stylist_id'), 'service_reviews', ['stylist_id'], unique=False)

    op.create_index(op.f('ix_service_reviews_user_id'), 'service_reviews', ['user_id'], unique=False)

    op.create_table('notification_send_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('recipient_id', sa.String(length=36), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=False),
    sa.Column('notification_id', sa.String(length=36), nullable=True),
    sa.Column('booking_id', sa.String(length=36), nullable=True),
    sa.Column('cycle_key', sa.String(length=160), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('send_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_notification_send_logs_actor_id'), 'notification_send_logs', ['actor_id'], unique=False)

    op.create_index(op.f('ix_notification_send_logs_booking_id'), 'notification_send_logs', ['booking_id'], unique=False)

    op.create_index('ix_notification_send_logs_cycle', 'notification_send_logs', ['cycle_key', 'recipient_id', 'type'], unique=False)

    op.create_index(op.f('ix_notification_send_logs_cycle_key'), 'notification_send_logs', ['cycle_key'], unique=False)

    op.create_index(op.f('ix_notification_send_logs_notification_id'), 'notification_send_logs', ['notification_id'], unique=False)

    op.create_index('ix_notification_send_logs_recipient_created', 'notification_send_logs', ['recipient_id', 'created_at'], unique=False)

    op.create_index(op.f('ix_notification_send_logs_recipient_id'), 'notification_send_logs', ['recipient_id'], unique=False)

    op.create_index(op.f('ix_notification_send_logs_type'), 'notification_send_logs', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_send_logs_type'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_recipient_id'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_recipient_created'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_notification_id'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_cycle_key'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_cycle'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_booking_id'), table_name='notification_send_logs')

    op.drop_index(op.f('ix_notification_send_logs_actor_id'), table_name='notification_send_logs')

    op.drop_table('notification_send_logs')

    op.drop_index(op.f('ix_service_reviews_user_id'), table_name='service_reviews')

    op.drop_index(op.f('ix_service_reviews_stylist_id'), table_name='service_reviews')

    op.drop_index(op.f('ix_service_reviews_salon_service_price_id'), table_name='service_reviews')

    op.drop_index(op.f('ix_service_reviews_salon_id'), table_name='service_reviews')

    op.drop_index(op.f('ix_service_reviews_id'), table_name='service_reviews')

    op.drop_index(op.f('ix_service_reviews_booking_id'), table_name='service_reviews')

    op.drop_table('service_reviews')

    op.drop_index(op.f('ix_notifications_recipient_unread'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_recipient_status_created'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_recipient_read_created'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_recipient_id'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_recipient_created'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_post_id'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_delivery_status'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_booking_id'), table_name='notifications')

    op.drop_index(op.f('ix_notifications_actor_created'), table_name='notifications')

    op.drop_table('notifications')

    op.drop_index(op.f('ix_chat_messages_sender_user_id'), table_name='chat_messages')

    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')

    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')

    op.drop_index(op.f('ix_chat_messages_conversation_id'), table_name='chat_messages')

    op.drop_index(op.f('ix_chat_messages_conversation_created'), table_name='chat_messages')

    op.drop_index(op.f('ix_chat_messages_booking_id'), table_name='chat_messages')

    op.drop_table('chat_messages')

    op.drop_index(op.f('ix_stylist_services_stylist_id'), table_name='stylist_services')

    op.drop_index(op.f('ix_stylist_services_salon_service_price_id'), table_name='stylist_services')

    op.drop_index(op.f('ix_stylist_services_id'), table_name='stylist_services')

    op.drop_table('stylist_services')

    op.drop_index(op.f('ix_stylist_ratings_user_id'), table_name='stylist_ratings')

    op.drop_index(op.f('ix_stylist_ratings_stylist_id'), table_name='stylist_ratings')

    op.drop_index(op.f('ix_stylist_ratings_id'), table_name='stylist_ratings')

    op.drop_table('stylist_ratings')

    op.drop_index(op.f('ix_saved_services_user_id'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_user_created'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_sub_service_id'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_sub_service_created'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_service_id'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_service_created'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_salon_service_price_id'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_salon_price_created'), table_name='saved_services')

    op.drop_index(op.f('ix_saved_services_id'), table_name='saved_services')

    op.drop_table('saved_services')

    op.drop_index(op.f('ix_salon_service_products_salon_service_price_id'), table_name='salon_service_products')

    op.drop_index(op.f('ix_salon_service_products_id'), table_name='salon_service_products')

    op.drop_table('salon_service_products')

    op.drop_index(op.f('ix_salon_service_benefits_salon_service_price_id'), table_name='salon_service_benefits')

    op.drop_index(op.f('ix_salon_service_benefits_id'), table_name='salon_service_benefits')

    op.drop_table('salon_service_benefits')

    op.drop_index(op.f('ix_post_views_user_viewed'), table_name='post_views')

    op.drop_index(op.f('ix_post_views_post_viewed'), table_name='post_views')

    op.drop_index(op.f('ix_post_views_id'), table_name='post_views')

    op.drop_table('post_views')

    op.drop_index(op.f('ix_post_shares_share_user'), table_name='post_shares')

    op.drop_index(op.f('ix_post_shares_received_user'), table_name='post_shares')

    op.drop_index(op.f('ix_post_shares_post_created_user'), table_name='post_shares')

    op.drop_table('post_shares')

    op.drop_index(op.f('ix_post_settings_id'), table_name='post_settings')

    op.drop_table('post_settings')

    op.drop_index(op.f('ix_post_reports_user_created'), table_name='post_reports')

    op.drop_index(op.f('ix_post_reports_post_status'), table_name='post_reports')

    op.drop_index(op.f('ix_post_reports_id'), table_name='post_reports')

    op.drop_table('post_reports')

    op.drop_index(op.f('ix_post_mentions_post_mentioned'), table_name='post_mentions')

    op.drop_index(op.f('ix_post_mentions_mentioned_created'), table_name='post_mentions')

    op.drop_index(op.f('ix_post_mentions_id'), table_name='post_mentions')

    op.drop_table('post_mentions')

    op.drop_index(op.f('ix_post_likes_user_created'), table_name='post_likes')

    op.drop_index(op.f('ix_post_likes_post_user'), table_name='post_likes')

    op.drop_index(op.f('ix_post_likes_post_liked'), table_name='post_likes')

    op.drop_index(op.f('ix_post_likes_id'), table_name='post_likes')

    op.drop_table('post_likes')

    op.drop_index(op.f('ix_post_hashtags_post_hashtag'), table_name='post_hashtags')

    op.drop_index(op.f('ix_post_hashtags_id'), table_name='post_hashtags')

    op.drop_index(op.f('ix_post_hashtags_hashtag_created'), table_name='post_hashtags')

    op.drop_table('post_hashtags')

    op.drop_index(op.f('ix_post_comments_user_rep'), table_name='post_comments')

    op.drop_index(op.f('ix_post_comments_user_created'), table_name='post_comments')

    op.drop_index(op.f('ix_post_comments_post_parent_created'), table_name='post_comments')

    op.drop_index(op.f('ix_post_comments_post_id'), table_name='post_comments')

    op.drop_index(op.f('ix_post_comments_id'), table_name='post_comments')

    op.drop_index(op.f('ix_post_comments_comment_id'), table_name='post_comments')

    op.drop_table('post_comments')

    op.drop_index(op.f('ix_post_bookmarks_user_post'), table_name='post_bookmarks')

    op.drop_index(op.f('ix_post_bookmarks_user_created'), table_name='post_bookmarks')

    op.drop_index(op.f('ix_post_bookmarks_id'), table_name='post_bookmarks')

    op.drop_table('post_bookmarks')

    op.drop_index(op.f('ix_post_analytics_id'), table_name='post_analytics')

    op.drop_table('post_analytics')

    op.drop_index(op.f('ix_media_data_post_created'), table_name='media_data')

    op.drop_index(op.f('ix_media_data_id'), table_name='media_data')

    op.drop_table('media_data')

    op.drop_index(op.f('ix_bookings_status'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_start_at'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_service_status_start'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_salon_status_start'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_salon_start'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_salon_service_price_id'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_salon_id'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_id'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_customer_status_start'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_customer_start'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_customer_id'), table_name='bookings')

    op.drop_index(op.f('ix_bookings_created'), table_name='bookings')

    op.drop_table('bookings')

    op.drop_index(op.f('ix_sponsored_salons_start_at'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_sponsored_salons_salon_id'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_sponsored_salons_plan_type'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_sponsored_salons_is_active'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_sponsored_salons_id'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_sponsored_salons_end_at'), table_name='sponsored_salons')

    op.drop_index(op.f('ix_active_sponsored_salon'), table_name='sponsored_salons')

    op.drop_table('sponsored_salons')

    op.drop_index(op.f('ix_saved_salons_user_id'), table_name='saved_salons')

    op.drop_index(op.f('ix_saved_salons_user_created'), table_name='saved_salons')

    op.drop_index(op.f('ix_saved_salons_salon_id'), table_name='saved_salons')

    op.drop_index(op.f('ix_saved_salons_salon_created'), table_name='saved_salons')

    op.drop_index(op.f('ix_saved_salons_id'), table_name='saved_salons')

    op.drop_table('saved_salons')

    op.drop_index(op.f('ix_salon_working_hours_salon_id'), table_name='salon_working_hours')

    op.drop_table('salon_working_hours')

    op.drop_index(op.f('ix_salon_stylists_user_id'), table_name='salon_stylists')

    op.drop_index(op.f('ix_salon_stylists_salon_id'), table_name='salon_stylists')

    op.drop_index(op.f('ix_salon_stylists_id'), table_name='salon_stylists')

    op.drop_table('salon_stylists')

    op.drop_index(op.f('ix_service_lookup'), table_name='salon_service_prices')

    op.drop_index(op.f('ix_salon_service_prices_status'), table_name='salon_service_prices')

    op.drop_index(op.f('ix_salon_service_prices_salon_id'), table_name='salon_service_prices')

    op.drop_index(op.f('ix_salon_service_prices_id'), table_name='salon_service_prices')

    op.drop_table('salon_service_prices')

    op.drop_index(op.f('ix_salon_reports_user_id'), table_name='salon_reports')

    op.drop_index(op.f('ix_salon_reports_user_created'), table_name='salon_reports')

    op.drop_index(op.f('ix_salon_reports_salon_id'), table_name='salon_reports')

    op.drop_index(op.f('ix_salon_reports_salon_created'), table_name='salon_reports')

    op.drop_index(op.f('ix_salon_reports_id'), table_name='salon_reports')

    op.drop_table('salon_reports')

    op.drop_index(op.f('ix_salon_locations_salon_id'), table_name='salon_locations')

    op.drop_table('salon_locations')

    op.drop_index(op.f('ix_salon_galleries_id'), table_name='salon_galleries')

    op.drop_table('salon_galleries')

    op.drop_index(op.f('ix_salon_followers_user_id'), table_name='salon_followers')

    op.drop_index(op.f('ix_salon_followers_user_created'), table_name='salon_followers')

    op.drop_index(op.f('ix_salon_followers_salon_id'), table_name='salon_followers')

    op.drop_index(op.f('ix_salon_followers_salon_created'), table_name='salon_followers')

    op.drop_index(op.f('ix_salon_followers_notifications'), table_name='salon_followers')

    op.drop_index(op.f('ix_salon_followers_id'), table_name='salon_followers')

    op.drop_table('salon_followers')

    op.drop_index(op.f('uq_primary_contact_per_type'), table_name='salon_contacts')

    op.drop_index(op.f('ix_salon_contacts_salon_id'), table_name='salon_contacts')

    op.drop_index(op.f('ix_salon_contacts_id'), table_name='salon_contacts')

    op.drop_table('salon_contacts')

    op.drop_index(op.f('ix_salon_blocks_user_id'), table_name='salon_blocks')

    op.drop_index(op.f('ix_salon_blocks_user_created'), table_name='salon_blocks')

    op.drop_index(op.f('ix_salon_blocks_salon_id'), table_name='salon_blocks')

    op.drop_index(op.f('ix_salon_blocks_salon_created'), table_name='salon_blocks')

    op.drop_index(op.f('ix_salon_blocks_id'), table_name='salon_blocks')

    op.drop_table('salon_blocks')

    op.drop_index(op.f('ix_salon_availability_overrides_salon_id'), table_name='salon_availability_overrides')

    op.drop_index(op.f('ix_salon_availability_overrides_salon_date'), table_name='salon_availability_overrides')

    op.drop_index(op.f('ix_salon_availability_overrides_date'), table_name='salon_availability_overrides')

    op.drop_table('salon_availability_overrides')

    op.drop_index(op.f('ix_rated_id'), table_name='rated')

    op.drop_table('rated')

    op.drop_index(op.f('ix_posts_user_created'), table_name='posts')

    op.drop_index(op.f('ix_posts_type_created'), table_name='posts')

    op.drop_index(op.f('ix_posts_sub_service_created'), table_name='posts')

    op.drop_index(op.f('ix_posts_status_created'), table_name='posts')

    op.drop_index(op.f('ix_posts_post_type'), table_name='posts')

    op.drop_index(op.f('ix_posts_id'), table_name='posts')

    op.drop_table('posts')

    op.drop_index(op.f('ix_chat_conversations_salon_user_last'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_salon_user_id'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_salon_id'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_last_message_at'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_id'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_customer_last'), table_name='chat_conversations')

    op.drop_index(op.f('ix_chat_conversations_customer_id'), table_name='chat_conversations')

    op.drop_table('chat_conversations')

    op.drop_index(op.f('ix_billing_subscriptions_salon_id'), table_name='billing_subscriptions')

    op.drop_index(op.f('ix_billing_subscriptions_id'), table_name='billing_subscriptions')

    op.drop_table('billing_subscriptions')

    op.drop_index(op.f('ix_verifications_token'), table_name='verifications')

    op.drop_index(op.f('ix_verifications_id'), table_name='verifications')

    op.drop_table('verifications')

    op.drop_index(op.f('ix_user_select_services_user_id'), table_name='user_select_services')

    op.drop_index(op.f('ix_user_select_services_id'), table_name='user_select_services')

    op.drop_table('user_select_services')

    op.drop_index(op.f('ix_user_notification_preferences_user_id'), table_name='user_notification_preferences')

    op.drop_table('user_notification_preferences')

    op.drop_index(op.f('ix_user_mutes_user_type_created'), table_name='user_mutes')

    op.drop_index(op.f('ix_user_mutes_user_id'), table_name='user_mutes')

    op.drop_index(op.f('ix_user_mutes_target_type'), table_name='user_mutes')

    op.drop_index(op.f('ix_user_mutes_target_id'), table_name='user_mutes')

    op.drop_table('user_mutes')

    op.drop_index(op.f('ix_user_device_tokens_user_id'), table_name='user_device_tokens')

    op.drop_index(op.f('ix_user_device_tokens_user_active'), table_name='user_device_tokens')

    op.drop_index(op.f('ix_user_device_tokens_token'), table_name='user_device_tokens')

    op.drop_table('user_device_tokens')

    op.drop_index(op.f('ix_sub_services_name'), table_name='sub_services')

    op.drop_index(op.f('ix_sub_services_id'), table_name='sub_services')

    op.drop_table('sub_services')

    op.drop_index(op.f('ix_search_histories_user_query'), table_name='search_histories')

    op.drop_index(op.f('ix_search_histories_user_id'), table_name='search_histories')

    op.drop_index(op.f('ix_search_histories_user_created'), table_name='search_histories')

    op.drop_index(op.f('ix_search_histories_id'), table_name='search_histories')

    op.drop_index(op.f('ix_search_histories_entity_entity_id'), table_name='search_histories')

    op.drop_table('search_histories')

    op.drop_index(op.f('ix_salons_user_id'), table_name='salons')

    op.drop_index(op.f('ix_salons_id'), table_name='salons')

    op.drop_table('salons')

    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')

    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')

    op.drop_table('refresh_tokens')

    op.drop_index(op.f('ix_profile_pictures_user_id'), table_name='profile_pictures')

    op.drop_index(op.f('ix_profile_pictures_id'), table_name='profile_pictures')

    op.drop_table('profile_pictures')

    op.drop_index(op.f('ix_customer_profiles_user_id'), table_name='customer_profiles')

    op.drop_table('customer_profiles')

    op.drop_index(op.f('ix_users_username'), table_name='users')

    op.drop_index(op.f('ix_users_role_access_created'), table_name='users')

    op.drop_index(op.f('ix_users_phone'), table_name='users')

    op.drop_index(op.f('ix_users_name'), table_name='users')

    op.drop_index(op.f('ix_users_id'), table_name='users')

    op.drop_index(op.f('ix_users_email'), table_name='users')

    op.drop_table('users')

    op.drop_index(op.f('ix_services_name'), table_name='services')

    op.drop_index(op.f('ix_services_id'), table_name='services')

    op.drop_table('services')

    op.drop_index(op.f('ix_hashtags_name'), table_name='hashtags')

    op.drop_index(op.f('ix_hashtags_id'), table_name='hashtags')

    op.drop_table('hashtags')

    # PostgreSQL enum types are not removed by DROP TABLE.
    sa.Enum('ACTIVE', 'BANNED', 'DELETED', 'LOCKED', 'PENDING', 'SUSPENDED', name='accountaccessstatus').drop(op.get_bind(), checkfirst=True)

    sa.Enum('PENDING', 'FAILED', 'SUCCESS', name='status').drop(op.get_bind(), checkfirst=True)

    sa.Enum('PUBLISHED', 'FLAGGED', 'DELETED', 'DRAFT', 'ARCHIVED', name='poststatus').drop(op.get_bind(), checkfirst=True)

    sa.Enum('ACTIVE', 'INACTIVE', 'ARCHIVED', name='servicecreatedstatus').drop(op.get_bind(), checkfirst=True)

    sa.Enum('PENDING', 'CONFIRMED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'NO_SHOW', name='bookingstatus').drop(op.get_bind(), checkfirst=True)

    sa.Enum('IMAGE', 'VIDEO', 'GIF', 'MIXED', name='mediatype').drop(op.get_bind(), checkfirst=True)

    sa.Enum('UPLOADED', 'PROCESSING', 'FAILED', 'PROCESSED', 'DELETED', name='mediastate').drop(op.get_bind(), checkfirst=True)

    sa.Enum('SPAM', 'INAPPROPRIATE', 'HARASSMENT', 'MISSINFORMATION', 'OTHER', name='reportreason').drop(op.get_bind(), checkfirst=True)

    sa.Enum('PENDING', 'REVIEWED', 'RESOLVED', 'REJECTED', 'ESCALATED', name='reportstatus').drop(op.get_bind(), checkfirst=True)

    sa.Enum('PUBLIC', 'FRIENDS', 'PRIVATE', name='postvisibility').drop(op.get_bind(), checkfirst=True)
