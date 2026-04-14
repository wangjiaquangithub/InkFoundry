"""Tests for Project Manager."""
from __future__ import annotations

import tempfile

import pytest

from Engine.core.project_manager import ProjectManager


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_create_project(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    project = pm.create_project("Test Novel", genre="xuanhuan")
    assert project.title == "Test Novel"
    assert project.genre == "xuanhuan"
    assert project.id is not None


def test_list_projects(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    pm.create_project("Novel 1")
    pm.create_project("Novel 2")
    projects = pm.list_projects()
    assert len(projects) == 2


def test_get_project(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    project = pm.create_project("Find Me")
    found = pm.get_project(project.id)
    assert found is not None
    assert found.title == "Find Me"


def test_get_nonexistent_project(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    assert pm.get_project("nonexistent") is None


def test_delete_project(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    project = pm.create_project("Delete Me")
    assert pm.delete_project(project.id) is True
    assert len(pm.list_projects()) == 0


def test_archive_project(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    project = pm.create_project("Archive Me")
    assert pm.archive_project(project.id) is True
    assert len(pm.list_projects()) == 0  # Not in "active" list


def test_default_genre(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir)
    project = pm.create_project("No Genre")
    assert project.genre == "unknown"
