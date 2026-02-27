"""Tests for chat response truncation handling."""

from app.services.chat_service import _ensure_complete_sentence


def test_ensure_complete_sentence_returns_complete_text_unchanged():
    text = "I want to quit smoking because of my grandson."
    assert _ensure_complete_sentence(text) == text


def test_ensure_complete_sentence_trims_to_last_sentence_boundary():
    text = "I want to be healthier.\" But I"
    assert _ensure_complete_sentence(text) == "I want to be healthier.\""


def test_ensure_complete_sentence_adds_terminal_period_when_needed():
    text = "I guess maybe that's a start"
    assert _ensure_complete_sentence(text).endswith(".")
