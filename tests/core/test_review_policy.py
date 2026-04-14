"""Tests for Review Policy Manager."""
from __future__ import annotations

from Engine.core.review_policy import ReviewPolicyManager


def test_strict_always_interrupts():
    mgr = ReviewPolicyManager("strict")
    assert mgr.should_interrupt({"score": 95, "critical_issues": []}) is True


def test_headless_never_interrupts():
    mgr = ReviewPolicyManager("headless")
    assert mgr.should_interrupt({"score": 10, "critical_issues": ["bad"]}) is False


def test_milestone_interrupts_on_critical():
    mgr = ReviewPolicyManager("milestone")
    assert mgr.should_interrupt({"score": 80, "critical_issues": ["plot hole"]}) is True


def test_milestone_no_interrupt_without_critical():
    mgr = ReviewPolicyManager("milestone")
    assert mgr.should_interrupt({"score": 80, "critical_issues": []}) is False


def test_set_policy():
    mgr = ReviewPolicyManager("strict")
    mgr.set_policy("headless")
    assert mgr.should_interrupt({"score": 0}) is False
