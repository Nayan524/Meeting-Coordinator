"""Scheduling behavior tests with deterministic calendar data."""

import unittest

from agent_relay.tools.scheduling import find_meeting_slots


class SchedulingTests(unittest.TestCase):
    def run_tool(self, duration=60, preference="afternoon", rows=None, day="2026-10-16"):
        offset = "-08:00" if day.endswith("12-16") else "-07:00"
        self.offset = offset
        return find_meeting_slots.invoke({
            "meeting_request": {
                "participants": ["alex@gmail.com", "priya@gmail.com"],
                "date": day, "duration_minutes": duration, "time_preference": preference,
            },
            "availability": {
                "start_time": f"{day}T08:00:00{offset}",
                "end_time": f"{day}T17:00:00{offset}",
                "participants": rows if rows is not None else [
                    {"email": "alex@gmail.com", "status": "success", "busy": []},
                    {"email": "priya@gmail.com", "status": "success", "busy": []},
                ],
            },
        })

    def test_merges_overlapping_touching_and_unsorted_intervals(self):
        def interval(start, end):
            return {"start": f"2026-10-16T{start}:00-07:00", "end": f"2026-10-16T{end}:00-07:00"}
        rows = [
            {"email": "alex@gmail.com", "status": "success", "busy": [interval("15:30", "16:00"), interval("12:00", "14:00")]},
            {"email": "priya@gmail.com", "status": "success", "busy": [interval("13:00", "14:30"), interval("16:00", "16:30")]},
        ]
        result = self.run_tool(duration=60, rows=rows)
        self.assertEqual(result["available_slots"], [{"start": "2026-10-16T14:30:00-07:00", "end": "2026-10-16T15:30:00-07:00"}])
        self.assertEqual(len(self.run_tool(duration=30, rows=rows)["available_slots"]), 2)

    def test_duration_and_preference(self):
        self.assertEqual(self.run_tool(duration=301)["available_slots"], [])
        slot = self.run_tool(preference="morning")["available_slots"][0]
        self.assertTrue(slot["start"].endswith("08:00:00-07:00"))
        self.assertTrue(slot["end"].endswith("12:00:00-07:00"))

    def test_missing_or_failed_participant_is_not_free(self):
        for rows in ([], [{"email": "alex@gmail.com", "status": "error"}]):
            with self.assertRaises(ValueError):
                self.run_tool(rows=rows)

    def test_unsupported_preference_and_missing_duration(self):
        for preference in (None, "after 2 PM"):
            with self.assertRaises(ValueError):
                self.run_tool(preference=preference)
        with self.assertRaises(ValueError):
            self.run_tool(duration=None)

    def test_winter_offset(self):
        slot = self.run_tool(day="2026-12-16")["available_slots"][0]
        self.assertTrue(slot["start"].endswith("12:00:00-08:00"))


if __name__ == "__main__":
    unittest.main()
