"""
JanRakshak AI
Offline AI Engine
"""

from offline_ai import OfflineAI


class AIEngine:

    def __init__(self):
        self.offline_ai = OfflineAI()

    def analyze(self, description):
        print("\n💻 Using Offline AI...\n")
        return self.offline_ai.analyze(description)