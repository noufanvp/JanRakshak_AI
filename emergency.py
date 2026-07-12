"""
JanRakshak AI
Emergency Contacts
"""


class EmergencyContacts:

    def __init__(self):

        self.contacts = {
            "Police": {
                "number": "100",
                "description": "For crimes, theft, violence and public safety."
            },

            "Fire & Rescue": {
                "number": "101",
                "description": "For fires, explosions and rescue operations."
            },

            "Ambulance": {
                "number": "108",
                "description": "Medical emergencies and ambulance services."
            },

            "Women Helpline": {
                "number": "1091",
                "description": "Support for women in distress."
            },

            "Child Helpline": {
                "number": "1098",
                "description": "Emergency assistance for children."
            },

            "Disaster Management": {
                "number": "1078",
                "description": "Floods, landslides, earthquakes and disasters."
            },

            "Electricity Department": {
                "number": "1912",
                "description": "Power failures and dangerous electrical issues."
            }
        }

    def show_contacts(self):

        print("\n" + "=" * 60)
        print("EMERGENCY CONTACTS")
        print("=" * 60)

        for department, info in self.contacts.items():

            print(f"\n{department}")
            print(f"Phone : {info['number']}")
            print(f"Info  : {info['description']}")

    def search_contact(self, keyword):

        keyword = keyword.lower()

        results = []

        for department, info in self.contacts.items():

            if keyword in department.lower():

                results.append((department, info))

        return results