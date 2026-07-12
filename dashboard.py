"""
JanRakshak AI
Advanced Analytics Dashboard
"""

from database import Database


class Dashboard:

    def __init__(self):
        self.db = Database()

    def show_dashboard(self):

        total_reports = self.db.get_total_reports()
        average_risk = self.db.get_average_risk()
        issue_data = self.db.get_reports_by_issue()
        priority_data = self.db.get_reports_by_priority()

        print("\n" + "=" * 70)
        print("                    JANRAKSHAK AI ANALYTICS")
        print("=" * 70)

        print(f"\n📄 Total Reports           : {total_reports}")
        print(f"📊 Average Risk Score      : {average_risk}")

        print("\n" + "=" * 70)
        print("ISSUE DISTRIBUTION")
        print("=" * 70)

        if issue_data:

            highest_issue = issue_data[0]

            for issue, count in issue_data:
                print(f"{issue:<30} : {count}")

            print("\nMost Common Issue")
            print(f"➡ {highest_issue[0]} ({highest_issue[1]} reports)")

        else:
            print("No reports available.")

        print("\n" + "=" * 70)
        print("PRIORITY DISTRIBUTION")
        print("=" * 70)

        priority_order = {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1
        }

        priority_data = sorted(
            priority_data,
            key=lambda x: priority_order.get(x[0], 0),
            reverse=True
        )

        if priority_data:

            for priority, count in priority_data:
                print(f"{priority:<30} : {count}")

        else:
            print("No reports available.")

        print("\n" + "=" * 70)

        if total_reports == 0:
            print("System Status : No reports available.")

        elif average_risk >= 80:
            print("System Status : 🔴 HIGH RISK")

        elif average_risk >= 50:
            print("System Status : 🟠 MODERATE RISK")

        else:
            print("System Status : 🟢 LOW RISK")

        print("=" * 70)