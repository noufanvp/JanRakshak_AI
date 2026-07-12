"""
JanRakshak AI
AI Memory
"""

from database import Database


class AIMemory:

    def __init__(self):
        self.db = Database()

    def remember(self, result):

        issue = result["Issue"]

        issue_count = self.db.get_issue_count(issue)

        most_common = self.db.get_most_common_issue()

        return {
            "Previous Reports": issue_count,
            "Most Common Issue": most_common[0] if most_common else "None"
        }