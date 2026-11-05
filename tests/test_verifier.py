from types import SimpleNamespace

from app.pool_service import verify_before_capture


def make_pool(status="open", target=100.0):
    return SimpleNamespace(status=status, target_amount=target)


def make_contrib(auth_id, amount):
    return SimpleNamespace(authorization_id=auth_id, amount=amount)


def test_passes_when_goal_met():
    ok, _ = verify_before_capture(
        make_pool(), [make_contrib("A1", 60.0), make_contrib("A2", 50.0)]
    )
    assert ok


def test_passes_when_exactly_at_goal():
    ok, _ = verify_before_capture(
        make_pool(), [make_contrib("A1", 60.0), make_contrib("A2", 40.0)]
    )
    assert ok


def test_blocks_below_goal():
    ok, reason = verify_before_capture(make_pool(), [make_contrib("A1", 60.0)])
    assert not ok
    assert "below goal" in reason


def test_blocks_when_pool_not_open():
    ok, reason = verify_before_capture(
        make_pool(status="funded"), [make_contrib("A1", 120.0)]
    )
    assert not ok
    assert "not open" in reason


def test_blocks_with_no_contributions():
    ok, _ = verify_before_capture(make_pool(), [])
    assert not ok


def test_blocks_missing_authorization_id():
    ok, reason = verify_before_capture(
        make_pool(), [make_contrib(None, 60.0), make_contrib("A2", 60.0)]
    )
    assert not ok
    assert "authorization" in reason


def test_blocks_duplicate_authorization():
    ok, reason = verify_before_capture(
        make_pool(), [make_contrib("A1", 60.0), make_contrib("A1", 60.0)]
    )
    assert not ok
    assert "duplicate" in reason