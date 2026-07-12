"""
JanRakshak AI
Main Application
"""

import os
import config

from ai_engine import AIEngine
from database import Database
from dashboard import Dashboard
from duplicate_detector import DuplicateDetector
from assistant import Assistant
from emergency import EmergencyContacts
from export_pdf import PDFExporter
from ai_memory import AIMemory
from hotspot import HotspotAnalyzer


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_title():
    print("=" * 60)
    print(config.Welcome_message)
    print("=" * 60)


def show_reports(reports):

    if not reports:
        print("\nNo reports found.")
        return

    labels = [
        "Report ID",
        "Description",
        "Location",
        "Issue",
        "Priority",
        "Department",
        "Confidence",
        "Advice",
        "Risk Score",
        "Reason",
        "Suggested Action"
    ]

    for report in reports:

        print("\n" + "-" * 60)

        for i, label in enumerate(labels):
            print(f"{label:<18}: {report[i]}")


def main_menu(ai, db, dashboard, assistant, emergency, pdf, memory, hotspot):

    detector = DuplicateDetector()

    while True:

        print("\nMAIN MENU")
        print("1. Report a New Issue")
        print("2. View Reports")
        print("3. AI Assistant")
        print("4. Emergency Contacts")
        print("5. Dashboard")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ").strip()

        if not choice.isdigit():
            print("\nInvalid input.")
            continue

        choice = int(choice)

        # --------------------------------------------------
        # REPORT NEW ISSUE
        # --------------------------------------------------

        if choice == 1:

            description = input(
                "\nDescribe the issue:\n\n"
            )

            location = input(
                "\nEnter the location of the issue:\n\n"
            ).strip()

            if not location:
                location = "Unknown"

            duplicate = detector.find_duplicate(
                description,
                db.get_reports()
            )

            if duplicate["duplicate"]:

                print("\n⚠ Similar report found!")
                print(f"Report ID : {duplicate['report_id']}")
                print(f"Similarity: {duplicate['similarity']}%")

                answer = input(
                    "\nDo you still want to save it? (y/n): "
                ).lower()

                if answer != "y":
                    print("\nReport cancelled.")
                    continue

            result = ai.analyze(description)

            memory_data = memory.remember(result)

            print("\n" + "=" * 60)
            print("AI ANALYSIS")
            print("=" * 60)

            print(f"Issue             : {result['Issue']}")
            print(f"Priority          : {result['Priority']}")
            print(f"Department        : {result['Department']}")
            print(f"Confidence        : {result['Confidence']}")
            print(f"Risk Score        : {result['Risk Score']}/100")
            print(f"Reason            : {result['Reason']}")
            print(f"Suggested Action  : {result['Suggested Action']}")
            print(f"Advice            : {result['Advice']}")

            print("\n" + "=" * 60)
            print("AI MEMORY")
            print("=" * 60)

            print(
                f"Previous Reports : {memory_data['Previous Reports']}"
            )

            print(
                f"Most Common Issue : {memory_data['Most Common Issue']}"
            )

            if memory_data["Previous Reports"] >= 5:

                print(
                    "\nThis appears to be a recurring civic issue."
                )

            elif memory_data["Previous Reports"] >= 2:

                print(
                    "\nSimilar reports already exist."
                )

            else:

                print(
                    "\nThis seems to be a relatively new issue."
                )

            db.save_report(
                description,
                location,
                result
            )

            hotspot_data = hotspot.analyze(location)

            print("\n" + "=" * 60)
            print("LOCATION ANALYSIS")
            print("=" * 60)

            print(f"Location          : {hotspot_data['Location']}")
            print(f"Previous Reports  : {hotspot_data['Previous Reports']}")
            print(f"Hotspot Level     : {hotspot_data['Hotspot Level']}")
            print(f"Recommendation    : {hotspot_data['Recommendation']}")

            print("\n✔ Report saved successfully.")

            pdf_choice = input(
                "\nGenerate PDF report? (y/n): "
            ).lower()

            if pdf_choice == "y":

                latest_report = db.get_reports()[0]

                filename = pdf.export(latest_report)

                print(f"\n✔ PDF saved at:\n{filename}")

        # --------------------------------------------------
        # VIEW REPORTS
        # --------------------------------------------------

        elif choice == 2:

            keyword = input(
                "\nSearch reports (leave blank for all): "
            ).strip()

            if keyword:
                reports = db.search_reports(keyword)
            else:
                reports = db.get_reports()

            show_reports(reports)

        # --------------------------------------------------
        # AI ASSISTANT
        # --------------------------------------------------

        elif choice == 3:
            print("\n" + "=" * 60)
            print("AI ASSISTANT")
            print("=" * 60)
            print("Type 'back' to return to the main menu.")

            while True:

                question = input("\nYou: ").strip()

                if question.lower() == "back":
                    break

                response = assistant.ask(question)

                print("\nTopic : " + response["Topic"])
                print("Answer: " + response["Answer"])

        # --------------------------------------------------
        # EMERGENCY CONTACTS
        # --------------------------------------------------

        elif choice == 4:

            while True:

                print("\n" + "=" * 60)
                print("EMERGENCY CONTACTS")
                print("=" * 60)
                print("1. Show All Contacts")
                print("2. Search Contact")
                print("3. Back")

                option = input("\nChoose: ").strip()

                if option == "1":

                    emergency.show_contacts()

                elif option == "2":

                    keyword = input(
                        "\nEnter department name: "
                    ).strip()

                    results = emergency.search_contact(keyword)

                    if not results:

                        print("\nNo matching contacts found.")

                    else:

                        print("\nResults")
                        print("-" * 40)

                        for department, info in results:

                            print(f"Department : {department}")
                            print(f"Phone      : {info['number']}")
                            print(f"Info       : {info['description']}")
                            print("-" * 40)

                elif option == "3":
                    break

                else:
                    print("Invalid option.")

        # --------------------------------------------------
        # DASHBOARD
        # --------------------------------------------------

        elif choice == 5:

            dashboard.show_dashboard()

        # --------------------------------------------------
        # EXIT
        # --------------------------------------------------

        elif choice == 6:

            print("\nThank you for using JanRakshak AI.")
            break

        else:

            print("\nInvalid choice.")


def main():

    clear_screen()

    ai = AIEngine()

    db = Database()

    dashboard = Dashboard()

    assistant = Assistant()

    memory = AIMemory()

    hotspot = HotspotAnalyzer()

    emergency = EmergencyContacts()

    pdf = PDFExporter()

    db.create_database()

    show_title()

    main_menu(
        ai,
        db,
        dashboard,
        assistant,
        emergency,
        pdf,
        memory,
        hotspot
    )


if __name__ == "__main__":
    main()