"""
JanRakshak AI
Hotspot Analyzer
"""

from database import Database


class HotspotAnalyzer:

    def __init__(self):
        self.db = Database()

    def analyze(self, location):

        count = self.db.get_location_count(location)

        if count >= 10:
            level = "CRITICAL"
            message = (
                "This location has a very high number of civic complaints."
            )

        elif count >= 5:
            level = "HIGH"
            message = (
                "This area has frequent civic complaints."
            )

        elif count >= 2:
            level = "MEDIUM"
            message = (
                "Multiple reports have been submitted from this location."
            )

        else:
            level = "LOW"
            message = (
                "This appears to be a relatively new location for reports."
            )

        return {
            "Location": location,
            "Previous Reports": count,
            "Hotspot Level": level,
            "Recommendation": message
        }