"""
JanRakshak AI
Offline AI Assistant
"""

class Assistant:

    def __init__(self):

        self.knowledge = {

            "road": (
                "Road Damage",
                "Road problems should be reported to the Public Works Department (PWD). "
                "If the damage is dangerous, avoid the area and warn other road users."
            ),

            "pothole": (
                "Road Damage",
                "Large potholes can damage vehicles and cause accidents. "
                "Report them to the Public Works Department."
            ),

            "garbage": (
                "Garbage",
                "Garbage collection issues should be reported to your local Municipality "
                "or Panchayat sanitation department."
            ),

            "waste": (
                "Garbage",
                "Illegal waste dumping should be reported to the local civic authority."
            ),

            "water": (
                "Water Leakage",
                "Water leakage should be reported to the Water Authority immediately."
            ),

            "pipe": (
                "Water Leakage",
                "Broken pipelines should be reported to the Water Authority."
            ),

            "streetlight": (
                "Streetlight",
                "Faulty streetlights should be reported to the Electricity Department "
                "or local Municipality."
            ),

            "light": (
                "Streetlight",
                "Streetlight problems reduce public safety during night hours."
            ),

            "fire": (
                "Fire",
                "Call Fire and Rescue immediately by dialing 101 if there is a fire."
            ),

            "electricity": (
                "Electricity",
                "Avoid touching damaged electrical equipment and report it immediately."
            ),

            "tree": (
                "Tree Fall",
                "Fallen trees should be reported to Disaster Management or Municipality."
            ),

            "flood": (
                "Flood",
                "Move to higher ground and follow instructions from Disaster Management."
            )
        }

    def ask(self, question):

        question = question.lower()

        for keyword in self.knowledge:

            if keyword in question:

                topic, answer = self.knowledge[keyword]

                return {
                    "Topic": topic,
                    "Answer": answer
                }

        return {
            "Topic": "General",
            "Answer": (
                "Sorry, I don't have information about that yet. "
                "Please contact your local civic authority."
            )
        }