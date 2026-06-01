import asyncio

from models.auth.user import User
from models.search.search import SearchHistory
from service.search.search import (
    clear_search_history_,
    delete_search_history_item_,
    list_search_history_,
    save_search_history_,
)
from tests.conftest import make_user


def test_search_history_save_list_delete_and_clear(db_session_factory):
    session_iter = db_session_factory([User.__table__, SearchHistory.__table__])
    db = next(session_iter)
    try:
        user = make_user(user_id="history-user")
        db.add(user)
        db.commit()

        asyncio.run(
            save_search_history_(
                db=db,
                user_id=user.id,
                query="braids 25000",
                entity="service",
                entity_id="offering-1",
            )
        )
        asyncio.run(
            save_search_history_(
                db=db,
                user_id=user.id,
                query="braids 25000",
                entity="service",
                entity_id="offering-1",
            )
        )

        history = list_search_history_(db=db, user_id=user.id, limit=10)
        assert len(history.items) == 1
        assert history.items[0].query == "braids 25000"
        assert history.items[0].entity == "service"
        assert history.items[0].entity_id == "offering-1"

        delete_search_history_item_(
            db=db,
            user_id=user.id,
            history_id=history.items[0].id,
        )
        assert list_search_history_(db=db, user_id=user.id, limit=10).items == []

        asyncio.run(
            save_search_history_(
                db=db,
                user_id=user.id,
                query="salon",
                entity="query",
                entity_id=None,
            )
        )
        clear_search_history_(db=db, user_id=user.id)
        assert list_search_history_(db=db, user_id=user.id, limit=10).items == []
    finally:
        try:
            next(session_iter)
        except StopIteration:
            pass
