import unittest

from scripts import g0_project_remediation as core
from scripts import g0_project_remediation_safe as safe


def snapshot(names):
    return {
        "project": {
            "views": {
                "nodes": [
                    {"id": f"VIEW_{index}", "name": name}
                    for index, name in enumerate(names)
                ]
            }
        }
    }


class ProvenBoardViewTests(unittest.TestCase):
    def canonical_names(self):
        return sorted(core.CANONICAL_VIEWS)

    def test_exact_sixth_board_view_is_authorized(self):
        names = self.canonical_names() + [safe.PROVEN_LEGACY_BOARD_VIEW]
        self.assertEqual(
            {safe.PROVEN_LEGACY_BOARD_VIEW},
            safe.proven_legacy_views(snapshot(names)),
        )

    def test_board_plus_another_unknown_view_is_not_authorized(self):
        names = self.canonical_names() + [safe.PROVEN_LEGACY_BOARD_VIEW, "99 — Неизвестное"]
        self.assertEqual(set(), safe.proven_legacy_views(snapshot(names)))

    def test_missing_canonical_view_is_not_authorized(self):
        names = self.canonical_names()[1:] + [safe.PROVEN_LEGACY_BOARD_VIEW]
        self.assertEqual(set(), safe.proven_legacy_views(snapshot(names)))

    def test_duplicate_view_name_is_not_authorized(self):
        names = self.canonical_names() + [safe.PROVEN_LEGACY_BOARD_VIEW, safe.PROVEN_LEGACY_BOARD_VIEW]
        self.assertEqual(set(), safe.proven_legacy_views(snapshot(names)))

    def test_authorization_does_not_mutate_global_legacy_allowlist(self):
        before = set(core.LEGACY_VIEWS)
        names = self.canonical_names() + [safe.PROVEN_LEGACY_BOARD_VIEW]
        safe.proven_legacy_views(snapshot(names))
        self.assertEqual(before, core.LEGACY_VIEWS)
        self.assertNotIn(safe.PROVEN_LEGACY_BOARD_VIEW, core.LEGACY_VIEWS)

    def test_ephemeral_authorization_builds_exact_delete_plan_and_restores_allowlist(self):
        names = self.canonical_names() + [safe.PROVEN_LEGACY_BOARD_VIEW]
        snap = snapshot(names)
        before = set(core.LEGACY_VIEWS)
        core.LEGACY_VIEWS.update(safe.proven_legacy_views(snap))
        try:
            deletion = core.view_delete_plan(snap)
        finally:
            core.LEGACY_VIEWS.clear()
            core.LEGACY_VIEWS.update(before)
        self.assertEqual(1, len(deletion))
        self.assertEqual(safe.PROVEN_LEGACY_BOARD_VIEW, deletion[0]["name"])
        self.assertTrue(deletion[0]["id"].startswith("VIEW_"))
        self.assertEqual(before, core.LEGACY_VIEWS)


if __name__ == "__main__":
    unittest.main()
