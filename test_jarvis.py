import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add Jarvis to path so it can import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main

class TestJarvis(unittest.TestCase):
    def setUp(self):
        # Prevent any UI interactions from failing
        main._app = MagicMock()
        main.ws_broadcast = MagicMock()
        
    @patch('main.webbrowser.open')
    @patch('main.sp_open')
    def test_routing_apps(self, mock_sp_open, mock_webbrowser):
        mock_sp_open.return_value = "Opening Spotify."
        # Test routing for apps and websites
        result = main.route("open spotify")
        self.assertTrue(mock_sp_open.called)
        self.assertEqual("Opening Spotify.", result)
        
        mock_webbrowser.reset_mock()
        result = main.route("open github")
        self.assertTrue(mock_webbrowser.called)
        self.assertEqual("Opening GitHub.", result)
        
        mock_webbrowser.reset_mock()
        result = main.route("search google for python tutorial")
        self.assertTrue(mock_webbrowser.called)
        self.assertIn("Searching Google for python tutorial", result)
        
    @patch('main.get_weather')
    def test_routing_weather(self, mock_get_weather):
        mock_get_weather.return_value = "Dublin: 15C"
        result = main.route("what is the weather in dublin")
        self.assertEqual(result, "Dublin: 15C")
        mock_get_weather.assert_called_with("Dublin")

    @patch('main.get_news')
    def test_routing_news(self, mock_get_news):
        mock_get_news.return_value = "News summary."
        result = main.route("tell me the news about ai")
        self.assertEqual(result, "News summary.")
        mock_get_news.assert_called_with("ai")
        
    @patch('main.log_workout')
    def test_routing_workout(self, mock_log_workout):
        mock_log_workout.return_value = "Workout logged: chest and back"
        result = main.route("log workout chest and back")
        self.assertEqual(result, "Workout logged: chest and back")
        mock_log_workout.assert_called_with("chest and back")

    @patch('main.log_meal')
    def test_routing_meal(self, mock_log_meal):
        mock_log_meal.return_value = "Meal logged."
        result = main.route("i ate chicken and rice")
        self.assertEqual(result, "Meal logged.")
        mock_log_meal.assert_called_with("chicken and rice")

    @patch('main.log_calories')
    def test_routing_calories(self, mock_log_calories):
        mock_log_calories.return_value = "Calories logged."
        result = main.route("i had 500 calories")
        self.assertEqual(result, "Calories logged.")
        mock_log_calories.assert_called_with(500)
        
    @patch('main.take_note')
    def test_routing_notes(self, mock_take_note):
        mock_take_note.return_value = "Note saved."
        result = main.route("take a note meeting at 5")
        self.assertEqual(result, "Note saved.")
        mock_take_note.assert_called_with("meeting at 5")

    @patch('main.get_calendar_events')
    def test_routing_calendar(self, mock_get_calendar_events):
        mock_get_calendar_events.return_value = "No events today."
        result = main.route("what do i have today")
        self.assertEqual(result, "No events today.")
        mock_get_calendar_events.assert_called_with(days=1)

    @patch('main.load_tasks')
    @patch('main.save_tasks')
    def test_routing_tasks(self, mock_save_tasks, mock_load_tasks):
        mock_load_tasks.return_value = []
        result = main.route("add task buy groceries")
        self.assertEqual(result, "Added: buy groceries.")
        mock_save_tasks.assert_called()

if __name__ == '__main__':
    unittest.main()
