import copy
import unittest
from scripts.project_view_authorization import authorize, MARKER, OWNER, REPOSITORY

SHA = 'a' * 40


def event():
    return {'repository': {'full_name': REPOSITORY}, 'action': 'created', 'issue': {'number': 150},
            'comment': {'author_association': 'OWNER', 'user': {'login': OWNER},
                        'body': MARKER + '\nexpected_head=' + SHA}}


class AuthorizationTests(unittest.TestCase):
    def check(self, data, actor=OWNER, ref='refs/heads/main'):
        return authorize('issue_comment', data, actor, SHA, ref)

    def test_exact_owner_command(self):
        self.assertEqual(SHA, self.check(event()))

    def test_owner_dispatch(self):
        self.assertEqual(SHA, authorize('workflow_dispatch', {'repository': {'full_name': REPOSITORY}, 'inputs': {'expected_head': SHA}}, OWNER, SHA, 'refs/heads/main'))

    def test_stale_quoted_duplicate_and_appended_commands_rejected(self):
        for body in [MARKER + '\nexpected_head=' + 'b'*40, '> ' + MARKER + '\nexpected_head=' + SHA,
                     MARKER + '\nexpected_head=' + SHA + '\nexpected_head=' + SHA,
                     MARKER + '\nexpected_head=' + SHA + '\nrun=anything']:
            data = event(); data['comment']['body'] = body
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.check(data)

    def test_wrong_issue_actor_author_association_branch_and_repo_rejected(self):
        for key, value in [('issue', {'number': 1}), ('repository', {'full_name': 'fork/KAT9I_OS'}), ('action', 'edited')]:
            data = event(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(data)
        for key, value in [('author_association', 'MEMBER'), ('user', {'login': 'intruder'})]:
            data = event(); data['comment'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(data)
        with self.assertRaises(ValueError):
            self.check(event(), actor='intruder')
        with self.assertRaises(ValueError):
            self.check(event(), ref='refs/heads/feature')


if __name__ == '__main__':
    unittest.main()
