"""Test the runbook generator."""

from argparse import Namespace


from al2023_gate import runbook


def _args(kind, name="my-asg", region="us-east-1", cluster=None, out=None):
    return Namespace(kind=kind, name=name, region=region, cluster=cluster, out=out)


def test_asg_runbook_generated(capsys):
    rc = runbook.run(_args("asg"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Auto Scaling Group" in out
    assert "my-asg" in out
    assert "instance-refresh" in out


def test_eks_runbook_mentions_nodegroup(capsys):
    rc = runbook.run(_args("eks", cluster="prod-cluster"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "node group" in out.lower() or "nodegroup" in out.lower()


def test_ecs_runbook_mentions_task_def(capsys):
    rc = runbook.run(_args("ecs"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "task" in out.lower()


def test_beanstalk_runbook_mentions_platform(capsys):
    rc = runbook.run(_args("beanstalk"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "beanstalk" in out.lower() or "platform" in out.lower()


def test_unknown_kind_returns_error(capsys):
    rc = runbook.run(_args("notakind"))
    assert rc == 2


def test_writes_to_file(tmp_path):
    outfile = tmp_path / "runbook.md"
    rc = runbook.run(_args("asg", out=str(outfile)))
    assert rc == 0
    assert outfile.exists()
    assert "Auto Scaling Group" in outfile.read_text()


def test_name_substituted(capsys):
    rc = runbook.run(_args("asg", name="payment-prod-asg"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "payment-prod-asg" in out
