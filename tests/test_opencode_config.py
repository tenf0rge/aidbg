"""Guard the opencode engine config: the three permission tiers exist and the
read-only tier keeps its source-protecting / network-denying guarantees."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "opencode" / "opencode.jsonc"


def test_config_present():
    assert CFG.is_file()


def test_three_permission_tiers_defined():
    text = CFG.read_text(encoding="utf-8")
    for tier in ('"readonly"', '"safe-edit"', '"edit"'):
        assert tier in text, f"missing agent tier {tier}"


def test_readonly_tier_denies_network_and_protects_source():
    text = CFG.read_text(encoding="utf-8")
    # readonly must deny outbound network and block file tools reaching the
    # source (which lives outside the run dir)
    assert '"external_directory": "deny"' in text
    assert '"webfetch": "deny"' in text
    assert '"websearch": "deny"' in text


def test_litellm_provider_template_present():
    # common API config template (opt-in, key via env — no secret in the file)
    text = CFG.read_text(encoding="utf-8")
    assert "litellm" in text
    assert "{env:LITELLM_API_KEY}" in text
    assert "sk-" not in text  # no real key committed
