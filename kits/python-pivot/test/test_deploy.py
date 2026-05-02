"""Test deploy plan rendering (no AWS calls)."""

from argparse import Namespace


from python_pivot import deploy


def test_build_plan_includes_all_stages():
    plan = deploy.build_plan(
        "myfn", "live", [5, 25, 50, 100], 60, "arn:aws:...:MyAlarm", "python3.12"
    )
    assert "myfn" in plan
    assert "python3.12" in plan
    assert "5%" in plan
    assert "25%" in plan
    assert "100%" in plan


def test_build_plan_mentions_rollback():
    plan = deploy.build_plan("f", "live", [10, 100], 30, "alarm1", "python3.12")
    assert "rollback" in plan.lower()


def test_build_plan_warns_without_alarm():
    plan = deploy.build_plan("f", "live", [10, 100], 30, None, "python3.12")
    assert "REFUSE" in plan or "none" in plan


def test_plan_only_prints_and_exits(capsys):
    args = Namespace(
        function="f",
        alias="live",
        runtime="python3.12",
        stages="5,50,100",
        dwell="30",
        alarm=None,
        profile=None,
        region=None,
        plan_only=True,
        apply=False,
    )
    rc = deploy.run(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Canary deployment plan" in out


def test_apply_without_alarm_fails(capsys):
    args = Namespace(
        function="f",
        alias="live",
        runtime="python3.12",
        stages="5,100",
        dwell="10",
        alarm=None,
        profile=None,
        region=None,
        plan_only=False,
        apply=True,
    )
    rc = deploy.run(args)
    assert rc == 2
