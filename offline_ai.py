"""
JanRakshak AI
Offline AI Engine
Version 2
"""


class OfflineAI:

    def __init__(self):

        self.categories = {

            "Road Damage": {
                "keywords": [
                    "road", "pothole", "bridge",
                    "crack", "highway", "street"
                ],
                "priority": "High",
                "department": "Public Works Department",
                "confidence": "92%",
                "risk": 82,
                "reason": "The report contains keywords related to damaged roads.",
                "action": "Inspect the road and schedule repairs immediately.",
                "advice": "Avoid the damaged road and drive carefully."
            },

            "Water Leakage": {
                "keywords": [
                    "water", "leak", "pipe",
                    "tap", "drain"
                ],
                "priority": "Medium",
                "department": "Water Authority",
                "confidence": "90%",
                "risk": 63,
                "reason": "Possible water supply leakage detected.",
                "action": "Send a maintenance team to inspect the leak.",
                "advice": "Avoid wasting water and report major leaks quickly."
            },

            "Garbage": {
                "keywords": [
                    "garbage", "trash",
                    "waste", "dirty",
                    "dustbin"
                ],
                "priority": "Medium",
                "department": "Municipality",
                "confidence": "91%",
                "risk": 54,
                "reason": "Waste management issue detected.",
                "action": "Schedule waste collection.",
                "advice": "Avoid direct contact with the waste."
            },

            "Fire Emergency": {
                "keywords": [
                    "fire", "smoke",
                    "burning", "flames"
                ],
                "priority": "Critical",
                "department": "Fire and Rescue",
                "confidence": "98%",
                "risk": 99,
                "reason": "Fire-related emergency detected.",
                "action": "Dispatch emergency responders immediately.",
                "advice": "Move away immediately and call emergency services."
            },

            "Electricity": {
                "keywords": [
                    "electric",
                    "wire",
                    "pole",
                    "current",
                    "transformer"
                ],
                "priority": "High",
                "department": "Electricity Board",
                "confidence": "93%",
                "risk": 86,
                "reason": "Electrical hazard detected.",
                "action": "Send an electrical maintenance team.",
                "advice": "Stay away from damaged electrical equipment."
            }

        }

    def analyze(self, description):

        text = description.lower()

        for issue, info in self.categories.items():

            if any(word in text for word in info["keywords"]):

                return {
                    "Issue": issue,
                    "Priority": info["priority"],
                    "Department": info["department"],
                    "Confidence": info["confidence"],
                    "Risk Score": info["risk"],
                    "Reason": info["reason"],
                    "Suggested Action": info["action"],
                    "Advice": info["advice"]
                }

        return {
            "Issue": "Unknown",
            "Priority": "Low",
            "Department": "General Administration",
            "Confidence": "55%",
            "Risk Score": 20,
            "Reason": "The issue could not be classified.",
            "Suggested Action": "Manual review required.",
            "Advice": "Please provide more details."
        }