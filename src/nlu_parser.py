import re
from dateutil.parser import parse, ParserError

class NLUParser:
    @staticmethod
    def parse(command):
        command = command.lower().strip()
        intent_patterns = {
            "greet": r"hello",
            "add_task": r"add task:(.+)",
            "schedule_task": r"(schedule task|schedule recurring):(.+?)( at | for | in )(.+)",
            "set_priority": r"set priority:(.+?)( to )(\d+)",
            "feedback": r"feedback:(.+?)( on )(like|good|dislike|bad)", # Feedback intent matches this structure
            "generate_blog": r"generate blog",
            "complete_task": r"complete task:(.+)",
            "review_completed": r"review completed",
            "list_tasks": r"list tasks",
            "clear_tasks": r"clear tasks",
            "exit": r"exit"
        }

        for intent, pattern in intent_patterns.items():
            match = re.match(pattern, command)
            if match:
                if intent == "add_task":
                    return {"action": "add", "desc": match.group(1).strip()}
                elif intent == "schedule_task":
                    desc = match.group(2).strip()
                    time_str = match.group(4).strip()
                    priority_match = re.search(r"\(priority:(\d+)\)", desc)
                    priority = 1
                    if priority_match:
                        try:
                            priority = max(1, min(5, int(priority_match.group(1))))
                            # Remove priority string from description only if it was successfully parsed
                            desc = desc.replace(priority_match.group(0), "").strip()
                        except ValueError:
                            priority = 1 # Fallback if parsing fails

                    # Remove extra 'recurring' word from description if present
                    if "recurring" in match.group(1):
                        desc = desc.replace("recurring", "").strip()

                    try:
                        parsed_time = parse(time_str, fuzzy=True)
                        time_match = parsed_time.strftime("%H:%M") # Just the time string
                        return {"action": "schedule", "desc": desc, "time": time_match, "recurring": "recurring" in command, "priority": priority}
                    except ParserError:
                        return {"action": "unknown", "message": f"Couldn’t parse time '{time_str}'."}
                elif intent == "set_priority":
                    return {"action": "set_priority", "task_time": match.group(1).strip(), "priority": int(match.group(3))}
                elif intent == "feedback":
                    suggestion = match.group(1).strip()
                    feedback_value_str = match.group(3)
                    feedback = 1 if "like" in feedback_value_str or "good" in feedback_value_str else -1 if "dislike" in feedback_value_str or "bad" in feedback_value_str else 0
                    # Remove 'response_text' from NLU result; ChattyAgent will craft it
                    return {"action": "feedback", "suggestion": suggestion, "feedback": feedback}
                elif intent == "generate_blog":
                    return {"action": "generate_blog"}
                elif intent == "complete_task":
                    return {"action": "complete", "identifier": match.group(1).strip()}
                elif intent == "review_completed":
                    return {"action": "review"}
                elif intent == "list_tasks":
                    return {"action": "list"}
                elif intent == "clear_tasks":
                    return {"action": "clear"}
                elif intent == "exit":
                    return {"action": "exit"}
        return {"action": "unknown"}