# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests

class ActionShowUpcomingEvents(Action):
    def name(self) -> Text:
        return "action_show_upcoming_events"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            # Adjust the URL if your Flask server is running elsewhere
            response = requests.get("http://localhost:5000/api/upcoming_events")
            if response.status_code == 200:
                events = response.json().get("events", [])
                if events:
                    events_text = "\n".join([f"{e['title']} on {e['date']}" for e in events])
                    dispatcher.utter_message(text=f"Here are the upcoming events:\n{events_text}")
                else:
                    dispatcher.utter_message(text="There are no upcoming events.")
            else:
                dispatcher.utter_message(text="Sorry, I couldn't fetch the events right now.")
        except Exception as e:
            dispatcher.utter_message(text=f"Error fetching events: {str(e)}")
        return []

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
