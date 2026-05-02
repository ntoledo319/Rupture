"""Test the Packer HCL template generator."""

from argparse import Namespace


from al2023_gate import packer


def _args(tmp_path, **overrides):
    base = dict(
        packages=None,
        from_list="docker,nginx1,python3.8",
        out=str(tmp_path / "build"),
        region="us-east-1",
        instance_type="t3.small",
        name="al2023-migration",
        arch="x86_64",
    )
    base.update(overrides)
    return Namespace(**base)


def test_generates_hcl_file(tmp_path):
    rc = packer.run(_args(tmp_path))
    assert rc == 0
    hcl = tmp_path / "build" / "al2023.pkr.hcl"
    assert hcl.exists()
    content = hcl.read_text()
    assert "packer" in content
    assert "amazon-ebs" in content
    assert "us-east-1" in content


def test_generates_migration_report(tmp_path):
    rc = packer.run(_args(tmp_path))
    assert rc == 0
    report = tmp_path / "build" / "migration-report.md"
    assert report.exists()
    content = report.read_text()
    assert "package migration report" in content.lower()
    assert "docker" in content
    assert "python3.8" in content


def test_remaps_renamed_packages_in_install_block(tmp_path):
    rc = packer.run(_args(tmp_path, from_list="nginx1,php7.4"))
    assert rc == 0
    hcl = (tmp_path / "build" / "al2023.pkr.hcl").read_text()
    # nginx1 → nginx, php7.4 → php8.2
    assert "nginx" in hcl
    assert "php8.2" in hcl


def test_reads_from_package_file(tmp_path):
    pkg_file = tmp_path / "pkgs.txt"
    pkg_file.write_text("# comment\ndocker\nnginx1\n\npython3.8\n")
    rc = packer.run(_args(tmp_path, packages=str(pkg_file), from_list=None))
    assert rc == 0
    assert (tmp_path / "build" / "al2023.pkr.hcl").exists()


def test_default_packages_when_nothing_provided(tmp_path):
    rc = packer.run(_args(tmp_path, packages=None, from_list=None))
    assert rc == 0
    hcl = (tmp_path / "build" / "al2023.pkr.hcl").read_text()
    # nginx is in the default list
    assert "nginx" in hcl
