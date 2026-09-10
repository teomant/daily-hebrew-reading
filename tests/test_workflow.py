from __future__ import annotations

import unittest

from src.common import ROOT


class WorkflowTests(unittest.TestCase):
    def test_generation_workflow_diagnoses_and_skips_default_same_day_append(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "generate-daily-v2.yml").read_text(encoding="utf-8")

        self.assertIn('cron: "37 1 * * *"', workflow)
        self.assertIn("EVENT_SCHEDULE: ${{ github.event.schedule || '' }}", workflow)
        self.assertIn("WORKFLOW_REF: ${{ github.workflow_ref }}", workflow)
        self.assertIn("WORKFLOW_SHA: ${{ github.workflow_sha }}", workflow)
        self.assertIn('default: "0"', workflow)
        self.assertIn('should_generate: ${{ steps.decision.outputs.should_generate }}', workflow)
        self.assertIn("already exists and no append was requested", workflow)
        self.assertIn("if: needs.inspect-trigger.outputs.should_generate == 'true'", workflow)

        inspection_job, generation_job = workflow.split("  generate-and-build:", maxsplit=1)
        self.assertIn("  inspect-trigger:", inspection_job)
        self.assertNotIn("OPENAI_API_KEY", inspection_job)
        self.assertIn("OPENAI_API_KEY", generation_job)


if __name__ == "__main__":
    unittest.main()
