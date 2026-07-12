"""
JanRakshak AI
Duplicate Report Detector
"""

from difflib import SequenceMatcher


class DuplicateDetector:

    def __init__(self, threshold=0.75):
        self.threshold = threshold

    def similarity(self, text1, text2):
        return SequenceMatcher(
            None,
            text1.lower(),
            text2.lower()
        ).ratio()

    def find_duplicate(self, new_description, reports):

        best_report = None
        best_score = 0

        for report in reports:

            report_id = report[0]
            description = report[1]

            score = self.similarity(
                new_description,
                description
            )

            if score > best_score:
                best_score = score
                best_report = report_id

        if best_score >= self.threshold:
            return {
                "duplicate": True,
                "report_id": best_report,
                "similarity": round(best_score * 100, 2)
            }

        return {
            "duplicate": False,
            "report_id": None,
            "similarity": round(best_score * 100, 2)
        }