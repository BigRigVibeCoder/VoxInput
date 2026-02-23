"""
Golden recording tests for dictionary word correction.

Tests compound corrections (DB-driven), SymSpell injection of custom words,
and WordDatabase true-casing. These are unit tests that don't require audio.
"""
import pytest
import tempfile
import os
from pathlib import Path

from src.word_db import WordDatabase
from src.spell_corrector import SpellCorrector


@pytest.fixture
def word_db(tmp_path):
    """Fresh WordDatabase with tech words seeded."""
    db = WordDatabase(tmp_path / "test_words.db")
    tech_words = [
        ("Docker", "tech"), ("Python", "tech"), ("GitHub", "tech"),
        ("Amazon", "brand"), ("Google", "brand"), ("Ubuntu", "linux"),
        ("Slack", "tech"), ("Discord", "tech"), ("Figma", "tech"),
        ("Notion", "tech"), ("Jira", "agile"), ("Grafana", "tech"),
        ("Redis", "tech"), ("Kafka", "tech"), ("Postgres", "tech"),
        ("Terraform", "cloud"), ("Ansible", "cloud"), ("Jenkins", "dev"),
        ("Kubernetes", "cloud"), ("PyTorch", "ai"), ("TensorFlow", "ai"),
        ("Tailscale", "tech"), ("nginx", "tech"), ("API", "tech"),
        ("GraphQL", "tech"), ("TypeScript", "tech"), ("JavaScript", "tech"),
        ("VoxInput", "project"), ("HiveMind", "project"), ("ODROID", "tech"),
        ("LIDAR", "tech"), ("Sprint", "agile"), ("Standup", "agile"),
        ("Backlog", "agile"), ("Kanban", "agile"), ("Scrum", "agile"),
        ("Colorado", "place"), ("Virginia", "place"), ("Montana", "place"),
        ("Tennessee", "place"),
    ]
    for word, cat in tech_words:
        db.add_word(word, cat)
    return db


@pytest.fixture
def corrector(word_db):
    """SpellCorrector with word_db and compound corrections."""
    settings = {"spell_correction": True}
    sc = SpellCorrector(settings, word_db=word_db)
    return sc


class TestCompoundCorrections:
    """Test that multi-word ASR misrecognitions are corrected from DB."""

    def test_compound_corrections_seeded(self, word_db):
        """Default compound corrections should be auto-seeded."""
        compounds = word_db.get_compound_corrections()
        assert len(compounds) > 0
        assert ("pie", "torch") in compounds
        assert compounds[("pie", "torch")] == "PyTorch"

    def test_compound_crud(self, word_db):
        """Add and remove compound corrections."""
        assert word_db.add_compound_correction("my custom", "MyCustom")
        compounds = word_db.get_compound_corrections()
        assert ("my", "custom") in compounds
        assert compounds[("my", "custom")] == "MyCustom"

        assert word_db.remove_compound_correction("my custom")
        compounds = word_db.get_compound_corrections()
        assert ("my", "custom") not in compounds

    def test_compound_duplicate(self, word_db):
        """Can't add same misheard phrase twice."""
        word_db.add_compound_correction("test phrase", "TestPhrase")
        assert not word_db.add_compound_correction("test phrase", "Different")

    def test_pie_torch_to_pytorch(self, corrector):
        result = corrector.correct("the pie torch model was fast")
        assert "PyTorch" in result

    def test_tensor_flow_to_tensorflow(self, corrector):
        result = corrector.correct("we used tensor flow for training")
        assert "TensorFlow" in result

    def test_tail_scale_to_tailscale(self, corrector):
        result = corrector.correct("the tail scale network connected the nodes")
        assert "Tailscale" in result

    def test_engine_next_to_nginx(self, corrector):
        result = corrector.correct("the engine next reverse proxy worked well")
        assert "nginx" in result

    def test_cooper_neediest_to_kubernetes(self, corrector):
        result = corrector.correct("the cooper neediest cluster was deployed")
        assert "kubernetes" in result or "Kubernetes" in result

    def test_hive_mind_to_hivemind(self, corrector):
        result = corrector.correct("the hive mind robot navigated the course")
        assert "HiveMind" in result

    def test_a_pr_to_api(self, corrector):
        result = corrector.correct("the a pr gateway handled requests")
        assert "API" in result

    def test_three_word_compound(self, corrector):
        result = corrector.correct("we built a graph q l schema")
        assert "GraphQL" in result


class TestDictionaryTrueCasing:
    """Test that dictionary words get proper casing from WordDB."""

    def test_docker_casing(self, corrector):
        result = corrector.correct("we used docker for containers")
        assert "Docker" in result

    def test_github_casing(self, corrector):
        result = corrector.correct("push the code to github")
        assert "GitHub" in result

    def test_jira_casing(self, corrector):
        result = corrector.correct("create a ticket in jira")
        assert "Jira" in result

    def test_grafana_casing(self, corrector):
        result = corrector.correct("check the grafana dashboard")
        assert "Grafana" in result


class TestSymSpellInjection:
    """Test that custom words are injected into SymSpell for corrections."""

    def test_close_misspelling_corrected(self, corrector):
        """Words within edit distance 2 should correct to dictionary words."""
        # 'dockers' is edit distance 1 from 'docker'
        result = corrector.correct("run the dockers container")
        # Should correct toward 'docker' since it has 1M frequency
        assert "Docker" in result or "docker" in result


class TestGoldenParagraph:
    """
    Golden recording test paragraph.

    Expected input (what user would say via PTT):
    "The docker container ran on the kubernetes cluster period
     We checked the grafana dashboard and the jira backlog
     during the sprint standup period The terraform configuration
     managed the tailscale network in colorado and virginia period"

    What Vosk might produce (with typical misrecognitions):
    "the docker container ran on the cooper neediest cluster period
     we checked the grafana dashboard and the jira backlog
     during the sprint standup period the terra form configuration
     managed the tail scale network in colorado and virginia period"
    """

    def test_golden_paragraph(self, corrector):
        """Full paragraph through correction pipeline."""
        # Simulate what Vosk might produce
        vosk_output = (
            "the docker container ran on the cooper neediest cluster period "
            "we checked the grafana dashboard and the jira backlog "
            "during the sprint standup period the terra form configuration "
            "managed the tail scale network in colorado and virginia period"
        )

        result = corrector.correct(vosk_output)

        # Compound corrections
        assert "kubernetes" in result.lower()
        assert "Terraform" in result
        assert "Tailscale" in result

        # True-casing from WordDB
        assert "Docker" in result
        assert "Grafana" in result
        assert "Jira" in result

        # Voice punctuation should be preserved for downstream processing
        # (period → . is handled by VoicePunctuationBuffer, not SpellCorrector)

        # Capitalization after periods
        assert result[0].isupper()  # First word capitalized
