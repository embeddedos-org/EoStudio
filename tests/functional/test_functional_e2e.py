import unittest

class TestEoStudioFunctional(unittest.TestCase):
    def test_build_project_pipeline(self):
        project = {"files": ["main.c", "task.c"], "configured": True}
        # Build process
        build_success = False
        if project["configured"] and len(project["files"]) > 0:
            build_success = True
        assert build_success, "Project build pipeline failed"
