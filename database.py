"""
JanRakshak AI
Database Management
"""

import sqlite3
import os


class Database:

    def __init__(self):

        self.data_folder = "data"
        self.database_file = os.path.join(
            self.data_folder,
            "reports.db"
        )

        os.makedirs(
            self.data_folder,
            exist_ok=True
        )

    # --------------------------------------------------
    # CREATE DATABASE
    # --------------------------------------------------

    def create_database(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            location TEXT,
            issue TEXT,
            priority TEXT,
            department TEXT,
            confidence TEXT,
            advice TEXT,
            risk_score INTEGER,
            reason TEXT,
            suggested_action TEXT
        )
        """)

        connection.commit()
        connection.close()

        print("✔ Database Ready")

    # --------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------

    def save_report(
        self,
        description,
        location,
        result
    ):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        INSERT INTO reports(
            description,
            location,
            issue,
            priority,
            department,
            confidence,
            advice,
            risk_score,
            reason,
            suggested_action
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            description,
            location,
            result["Issue"],
            result["Priority"],
            result["Department"],
            result["Confidence"],
            result["Advice"],
            result["Risk Score"],
            result["Reason"],
            result["Suggested Action"]
        ))

        connection.commit()
        connection.close()

        print("✔ Report Saved")

    # --------------------------------------------------
    # GET ALL REPORTS
    # --------------------------------------------------

    def get_reports(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
        """)

        reports = cursor.fetchall()

        connection.close()

        return reports

    # --------------------------------------------------
    # SEARCH REPORTS
    # --------------------------------------------------

    def search_reports(self, keyword):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT *
        FROM reports
        WHERE
            description LIKE ?
            OR location LIKE ?
            OR issue LIKE ?
            OR priority LIKE ?
            OR department LIKE ?
        ORDER BY id DESC
        """, (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%"
        ))

        reports = cursor.fetchall()

        connection.close()

        return reports

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    def get_total_reports(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM reports"
        )

        total = cursor.fetchone()[0]

        connection.close()

        return total

    def get_reports_by_issue(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT issue, COUNT(*)
        FROM reports
        GROUP BY issue
        ORDER BY COUNT(*) DESC
        """)

        data = cursor.fetchall()

        connection.close()

        return data
    def get_reports_by_priority(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT priority, COUNT(*)
        FROM reports
        GROUP BY priority
        ORDER BY COUNT(*) DESC
        """)

        data = cursor.fetchall()

        connection.close()

        return data

    # --------------------------------------------------
    # AVERAGE RISK SCORE
    # --------------------------------------------------

    def get_average_risk(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT AVG(risk_score)
        FROM reports
        """)

        average = cursor.fetchone()[0]

        connection.close()

        if average is None:
            return 0

        return round(average, 2)

    # --------------------------------------------------
    # AI MEMORY
    # --------------------------------------------------

    def get_issue_count(self, issue):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE issue = ?
        """, (issue,))

        count = cursor.fetchone()[0]

        connection.close()

        return count

    def get_most_common_issue(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT issue, COUNT(*)
        FROM reports
        GROUP BY issue
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """)

        result = cursor.fetchone()

        connection.close()

        return result

    # --------------------------------------------------
    # LOCATION ANALYTICS
    # --------------------------------------------------

    def get_location_count(self, location):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE location = ?
        """, (location,))

        count = cursor.fetchone()[0]

        connection.close()

        return count

    def get_top_locations(self):

        connection = sqlite3.connect(
            self.database_file
        )

        cursor = connection.cursor()

        cursor.execute("""
        SELECT
            location,
            COUNT(*)
        FROM reports
        GROUP BY location
        ORDER BY COUNT(*) DESC
        LIMIT 5
        """)

        data = cursor.fetchall()

        connection.close()

        return data