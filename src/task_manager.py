# task_manager.py
from collections import defaultdict
import json
import os
from datetime import datetime, timedelta
import re # Import re for regular expressions

class TaskManager:
    def __init__(self):
        self.tasks = {} # Ad-hoc tasks
        self.scheduled_tasks = {} # Scheduled tasks
        self.completed_tasks = {} # Completed tasks
        self.task_history = defaultdict(int) # History for suggestions
        self.feedback_history = defaultdict(int) # Feedback for suggestions
        self.last_notified = {} # To prevent repeated alerts

    def add_task(self, desc, timestamp):
        self.tasks[timestamp] = desc
        self.task_history[desc.lower()] += 1
        return f"Yay! Added task: {desc} at {timestamp}!" # Return response text

    def schedule_task(self, desc, scheduled_datetime, recurring, priority):
        timestamp_key = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")
        # Clean desc from priority string if present, as it was already parsed by NLU
        cleaned_desc = desc
        priority_match = re.search(r"\(priority:(\d+)\)", cleaned_desc, re.IGNORECASE)
        if priority_match:
            cleaned_desc = cleaned_desc.replace(priority_match.group(0), "").strip()

        self.scheduled_tasks[timestamp_key] = {"desc": cleaned_desc, "recurring": recurring, "priority": priority}
        return f"Woo-hoo! Scheduled '{cleaned_desc}' (Priority: {priority}) for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!"

    def complete_task(self, identifier):
        found_task_data = None
        original_timestamp = None

        # Check ad-hoc tasks first
        for timestamp in list(self.tasks.keys()):
            if identifier.lower() in timestamp.lower() or identifier.lower() in self.tasks[timestamp].lower():
                found_task_data = {"desc": self.tasks.pop(timestamp), "timestamp": timestamp}
                original_timestamp = timestamp
                break

        # If not found in ad-hoc, check scheduled tasks
        if not found_task_data:
            for timestamp in list(self.scheduled_tasks.keys()):
                task_data = self.scheduled_tasks.get(timestamp)
                if task_data and (identifier.lower() in timestamp.lower() or identifier.lower() in task_data["desc"].lower()):
                    found_task_data = {"desc": self.scheduled_tasks.pop(timestamp)["desc"], "timestamp": timestamp}
                    original_timestamp = timestamp
                    break

        if found_task_data:
            desc = found_task_data["desc"]
            self.completed_tasks[original_timestamp] = desc
            self.task_history[desc.lower()] += 1
            return desc, original_timestamp # Return desc and its original timestamp
        return None, None # Indicate no task found

    def set_priority(self, task_identifier, new_priority):
        # Allow setting priority by partial match on description or timestamp
        for timestamp in list(self.scheduled_tasks.keys()):
            task_data = self.scheduled_tasks.get(timestamp)
            if task_data and (task_identifier.lower() in timestamp.lower() or task_identifier.lower() in task_data["desc"].lower()):
                task_data["priority"] = new_priority
                return task_data["desc"], timestamp # Return description and timestamp of updated task
        return None, None # Indicate no task found

    def clear_tasks(self):
        self.tasks.clear()
        self.scheduled_tasks.clear()
        self.completed_tasks.clear()
        self.task_history.clear()
        self.feedback_history.clear()
        # No return value needed, ChattyAgent will craft the response

    def get_completed_tasks_display(self): # New method to return display string
        if self.completed_tasks:
            return "Completed tasks:\n" + "\n".join(f"- {t}: {d}" for t, d in sorted(self.completed_tasks.items()))
        else:
            return "No tasks completed yet!"

    def get_all_tasks_display(self): # New method to return display string
        active_list_items = []
        for t, d in self.tasks.items():
            active_list_items.append(f"- {t}: {d}")
        # Make sure to format scheduled tasks consistently
        for t, v in self.scheduled_tasks.items():
            active_list_items.append(f"- {t}: {v['desc']} (Priority: {v.get('priority', 1)})")

        active_display = "Your tasks:\n" + "\n".join(sorted(active_list_items)) if active_list_items else ""

        completed_display = ""
        if self.completed_tasks:
            completed_display = "\nCompleted tasks:\n" + "\n".join(f"- {t}: {d}" for t, d in sorted(self.completed_tasks.items()))

        if not active_list_items and not self.completed_tasks:
            return "No tasks yet—give me something to do!"
        
        return active_display + completed_display

    def check_and_update_scheduled_tasks(self):
        """
        Checks scheduled tasks, updates recurring tasks, and returns alert messages.
        This method manages task data only, not UI or sounds.
        """
        current_datetime = datetime.now()
        alerts = []
        
        for timestamp_key in list(self.scheduled_tasks.keys()):
            task_data = self.scheduled_tasks.get(timestamp_key)
            if not task_data:
                continue

            try:
                scheduled_dt = datetime.strptime(timestamp_key, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"Warning: Invalid timestamp format for '{timestamp_key}'. Removing task from scheduled_tasks.")
                del self.scheduled_tasks[timestamp_key]
                continue
            
            # Use a fine-grained key for last_notified to avoid over-alerting
            alert_check_key = f"{timestamp_key}-{current_datetime.strftime('%Y%m%d%H%M')}" 
            
            # Check if current time is past or equal to scheduled time
            # And if we haven't already notified for this exact minute (for non-recurring) or day (for recurring)
            has_alerted_recently = False
            if task_data["recurring"]:
                # For recurring, check if already alerted today for this task key
                if timestamp_key in self.last_notified and self.last_notified[timestamp_key].get("last_alert_day") == current_datetime.date().strftime("%Y-%m-%d"):
                    has_alerted_recently = True
            else:
                # For one-time, check if alerted at this specific minute for this task key
                if timestamp_key in self.last_notified and self.last_notified[timestamp_key].get("last_alert_minute") == current_datetime.strftime("%Y-%m-%d %H:%M"):
                    has_alerted_recently = True

            if current_datetime >= scheduled_dt and not has_alerted_recently:
                alert_message = f"⏰ Alert! Time to {task_data['desc']} at {scheduled_dt.strftime('%Y-%m-%d %H:%M')}"
                alerts.append(alert_message)
                
                # Update last_notified record
                if timestamp_key not in self.last_notified:
                    self.last_notified[timestamp_key] = {}
                
                if task_data["recurring"]:
                    self.last_notified[timestamp_key]["last_alert_day"] = current_datetime.date().strftime("%Y-%m-%d")
                    
                    # Schedule for next day
                    new_scheduled_dt = scheduled_dt + timedelta(days=1)
                    new_timestamp_key = new_scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")
                    self.scheduled_tasks[new_timestamp_key] = task_data
                    del self.scheduled_tasks[timestamp_key] # Remove old key
                    print(f"Rescheduled recurring task '{task_data['desc']}' for {new_scheduled_dt.strftime('%Y-%m-%d %H:%M')}.")
                else:
                    self.last_notified[timestamp_key]["last_alert_minute"] = current_datetime.strftime("%Y-%m-%d %H:%M")
                    del self.scheduled_tasks[timestamp_key] # Remove one-time task
                    print(f"One-time task '{task_data['desc']}' completed and removed from scheduled.")
        return alerts

    def suggest_task(self): # Now this method belongs to TaskManager
        current_time = datetime.now()
        suggestions = []
        for timestamp, task_data in self.scheduled_tasks.items():
            try:
                scheduled_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue # Skip malformed timestamps

            time_diff = (scheduled_dt - current_time).total_seconds() / 60
            if 0 < time_diff <= 120: # Tasks due in next 2 hours
                urgency = max(1, 120 - time_diff) # More urgent closer to now
                priority_score = urgency * task_data["priority"]
                suggestions.append((priority_score, f"Schedule {task_data['desc']} at {scheduled_dt.strftime('%H:%M')} (in {int(time_diff)} minutes, Priority: {task_data['priority']})"))
        
        if suggestions:
            suggestions.sort(key=lambda x: x[0], reverse=True) # Sort by priority score
            return suggestions[0][1]

        if self.task_history:
            adjusted_history = {}
            for task, frequency in self.task_history.items():
                feedback = self.feedback_history.get(task.lower(), 0)
                # Adjust score based on feedback: positive feedback increases likelihood, negative decreases
                adjusted_score = frequency * (1 + feedback) # Feedback of 1 makes it 2x, -1 makes it 0x
                if adjusted_score > 0: # Only suggest tasks with positive adjusted score
                    adjusted_history[task] = adjusted_score
            
            if adjusted_history:
                most_frequent_task = max(adjusted_history.items(), key=lambda x: x[1])[0]
                
                # Suggest for the next hour, handling day rollover
                suggested_time_dt = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                # If the calculated next hour is earlier than now (e.g., 23:00 -> 00:00), it means it's the next day
                if suggested_time_dt.hour < current_time.hour: # Check if hour wrapped around midnight
                    suggested_time_dt += timedelta(days=1)

                return f"Based on your habits, how about scheduling {most_frequent_task} at {suggested_time_dt.strftime('%H:%M')}? (Provide feedback with 'feedback:{most_frequent_task} on like/good' or 'dislike/bad')"
        
        # Default time-based suggestions
        current_hour = current_time.hour
        if 12 <= current_hour < 14:
            return "Perhaps it's time to schedule lunch around 12:30?"
        elif 17 <= current_hour < 19:
            return "Maybe schedule dinner prep for 17:30?"
        elif 21 <= current_hour < 23:
            return "Don't forget to schedule your bedtime routine around 22:00?"
        return "No specific suggestions right now—add your own task!"

    def save_state(self, file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "tasks": self.tasks,
                    "scheduled_tasks": self.scheduled_tasks,
                    "completed_tasks": self.completed_tasks,
                    "task_history": dict(self.task_history),
                    "feedback_history": dict(self.feedback_history),
                    "last_notified": self.last_notified # Save last_notified as well
                }, f, indent=4)
            print(f"Saved tasks and history to {file_path}")
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def load_state(self, file_path):
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", {})
                    self.scheduled_tasks = data.get("scheduled_tasks", {})
                    self.completed_tasks = data.get("completed_tasks", {})
                    self.task_history = defaultdict(int, data.get("task_history", {}))
                    self.feedback_history = defaultdict(int, data.get("feedback_history", {}))
                    self.last_notified = data.get("last_notified", {}) # Load last_notified
                print(f"Loaded tasks and history from {file_path}")
            except json.JSONDecodeError as e:
                print(f"Error loading tasks: Invalid JSON. Starting fresh. Error: {e}")
            except Exception as e:
                print(f"Unexpected error loading tasks: {e}. Starting fresh.")
        else:
            print(f"No task file found at {file_path}. Starting fresh.")