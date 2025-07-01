from collections import defaultdict
import json
import os
from datetime import datetime

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.scheduled_tasks = {}
        self.completed_tasks = {}
        self.task_history = defaultdict(int)
        self.feedback_history = defaultdict(int)
        self.last_notified = {}

    def add_task(self, desc, timestamp):
        self.tasks[timestamp] = desc
        self.task_history[desc.lower()] += 1

    def schedule_task(self, desc, scheduled_datetime, recurring, priority):
        timestamp_key = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")
        self.scheduled_tasks[timestamp_key] = {"desc": desc, "recurring": recurring, "priority": priority}

    def complete_task(self, identifier):
        for timestamp in list(self.tasks.keys()):
            if identifier in timestamp.lower() or identifier in self.tasks[timestamp].lower():
                desc = self.tasks.pop(timestamp)
                self.completed_tasks[timestamp] = desc
                self.task_history[desc.lower()] += 1
                return desc, timestamp
        for timestamp in list(self.scheduled_tasks.keys()):
            task_data = self.scheduled_tasks.get(timestamp)
            if task_data and (identifier in timestamp.lower() or identifier in task_data["desc"].lower()):
                desc = self.scheduled_tasks.pop(timestamp)["desc"]
                self.completed_tasks[timestamp] = desc
                self.task_history[desc.lower()] += 1
                return desc, timestamp
        return None, None

    def set_priority(self, task_time, new_priority):
        for timestamp in list(self.scheduled_tasks.keys()):
            if task_time in timestamp:
                self.scheduled_tasks[timestamp]["priority"] = new_priority
                return self.scheduled_tasks[timestamp]["desc"], timestamp
        return None, None

    def clear_tasks(self):
        self.tasks.clear()
        self.scheduled_tasks.clear()
        self.completed_tasks.clear()
        self.task_history.clear()
        self.feedback_history.clear()

    def save_state(self, file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "tasks": self.tasks,
                    "scheduled_tasks": self.scheduled_tasks,
                    "completed_tasks": self.completed_tasks,
                    "task_history": dict(self.task_history),
                    "feedback_history": dict(self.feedback_history)
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
                print(f"Loaded tasks and history from {file_path}")
            except json.JSONDecodeError as e:
                print(f"Error loading tasks: Invalid JSON. Starting fresh. Error: {e}")
            except Exception as e:
                print(f"Unexpected error loading tasks: {e}. Starting fresh.")
        else:
            print(f"No task file found at {file_path}. Starting fresh.")