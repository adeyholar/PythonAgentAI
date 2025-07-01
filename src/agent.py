import numpy as np  # Not directly used, consider removing if unused
import pygame
import json
from datetime import datetime, timedelta
import os
import time
import random
from dateutil.parser import parse, ParserError  # Import ParserError for better error handling
from collections import defaultdict

# --- Configuration Constants ---
DATA_DIR = "agent_data"
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
ALERT_SOUND_FILE = "alert.wav"
BEEP_SOUND_FILE = "beep.wav"
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
FONT_SIZE = 24
TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (30, 30, 30)
AGENT_COLOR_IDLE = (0, 200, 255)  # Light Blue
AGENT_COLOR_GREETING = (0, 255, 0)  # Green
AGENT_COLOR_EXITING = (255, 0, 0)  # Red
AGENT_COLOR_ALERT = (255, 165, 0)  # Orange for alerts
CHECK_INTERVAL = 5  # Check tasks every 5 seconds to reduce CPU usage

class ChattyAgent:
    def __init__(self):
        # --- Agent State & Data ---
        self.state = "idle"  # Current visual/functional state
        self.tasks = {}  # General tasks (timestamp: desc)
        self.scheduled_tasks = {}  # Scheduled tasks (timestamp: {"desc": ..., "recurring": ..., "priority": ...})
        self.completed_tasks = {}  # Completed tasks (timestamp: desc)
        self.personality = "cheerful"
        self.input_buffer = ""
        self.response_display = []  # Stores recent responses for display
        self.max_response_lines = 10  # Max lines to show in response area
        self.task_history = defaultdict(int)  # Track completed task frequency

        # --- UI Components ---
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Chatty Agent")
        self.font = pygame.font.Font(None, FONT_SIZE)

        # --- Sound Components ---
        pygame.mixer.init()
        self.alert_sound = self._load_sound(ALERT_SOUND_FILE)
        self.beep_sound = self._load_sound(BEEP_SOUND_FILE)
        self.last_notified = {}  # Track last notification time per task

        # --- Data Persistence ---
        self._load_state()

    def _load_sound(self, filename):
        """Helper to load sound files with error handling."""
        try:
            return pygame.mixer.Sound(filename)
        except pygame.error:
            print(f"Warning: Could not load sound file '{filename}'. Notifications might be silent or incomplete.")
            return None

    def _load_state(self):
        """Loads tasks, scheduled_tasks, completed_tasks, and task_history from JSON file."""
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", {})
                    self.scheduled_tasks = data.get("scheduled_tasks", {})
                    self.completed_tasks = data.get("completed_tasks", {})
                    self.task_history = defaultdict(int, data.get("task_history", {}))
                print(f"Loaded tasks and history from {TASKS_FILE}")
            except json.JSONDecodeError as e:
                print(f"Error loading tasks from {TASKS_FILE}: Invalid JSON. Starting fresh. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while loading tasks: {e}. Starting fresh.")
        else:
            print(f"No existing task file found at {TASKS_FILE}. Starting fresh.")

    def _save_state(self):
        """Saves current task state and history to JSON file."""
        os.makedirs(DATA_DIR, exist_ok=True)  # Ensure data directory exists
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "tasks": self.tasks,
                    "scheduled_tasks": self.scheduled_tasks,
                    "completed_tasks": self.completed_tasks,
                    "task_history": dict(self.task_history)
                }, f, indent=4)
            print(f"Saved tasks and history to {TASKS_FILE}")
        except Exception as e:
            print(f"Error saving tasks to {TASKS_FILE}: {e}")

    def _add_response_to_display(self, response):
        """Adds a response string to the display buffer, splitting into lines."""
        for line in response.split('\n'):
            self.response_display.append(line)
        if len(self.response_display) > self.max_response_lines:
            self.response_display = self.response_display[-self.max_response_lines:]

    def parse_nlu(self, command):
        """Parses user command to determine action and extract entities."""
        print(f"Parsing command: '{command}'")  # Debugging output
        command = command.lower().strip()

        if "hello" in command:
            return {"action": "greet"}

        elif "add task" in command and ":" in command:
            parts = command.split(":", 1)
            desc = parts[1].strip()
            if not desc:
                return {"action": "unknown", "message": "Please provide a task description after 'add task:'!"}
            return {"action": "add", "desc": desc}

        elif any(kw in command for kw in ["schedule task", "schedule recurring", "set priority"]) and ":" in command:
            parts = command.split(":", 1)
            action_part = parts[0].strip()
            remaining = parts[1].strip()
            # Extract description and optional priority
            desc_with_priority = remaining.split(" at ")[0].strip() if " at " in remaining else remaining.split(" for ")[0].strip() if " for " in remaining else remaining.split(" in ")[0].strip()
            priority = 1  # Default priority
            if "(" in desc_with_priority and ")" in desc_with_priority:
                desc_part, prio_part = desc_with_priority.rsplit("(", 1)
                desc = desc_part.strip()
                if "priority" in prio_part.lower() and ")" in prio_part:
                    prio_value = prio_part.split("priority:")[1].split(")")[0].strip()
                    try:
                        priority = max(1, min(5, int(prio_value)))  # Clamp priority between 1 and 5
                    except ValueError:
                        priority = 1  # Default if parsing fails
            else:
                desc = desc_with_priority

            if not desc:
                return {"action": "unknown", "message": f"Please provide a task description after '{action_part}:' (e.g., 'schedule task:check desk at 1:15')!"}

            time_match = None
            if "schedule task" in action_part or "schedule recurring" in action_part:
                time_keywords = ["at", "for", "in"]
                for keyword in time_keywords:
                    if keyword in remaining:
                        time_str = next((s.strip() for s in remaining.split(keyword)[1:] if s.strip()), "")
                        if time_str:
                            try:
                                parsed_time = parse(time_str, fuzzy=True)
                                time_match = parsed_time.strftime("%H:%M")
                                break
                            except ParserError:
                                continue
                if not time_match:
                    return {"action": "unknown", "message": f"Please specify a time after '{desc}' using 'at', 'for', or 'in' with a format like '1:15 PM' or '13:15'!"}
                recurring = "recurring" in command
                return {"action": "schedule", "desc": desc, "time": time_match, "recurring": recurring, "priority": priority}
            elif "set priority" in action_part and ":" in remaining:
                task_time = remaining.split(" to ")[0].strip() if " to " in remaining else remaining
                new_priority_str = remaining.split(" to ")[1].strip() if " to " in remaining else ""
                try:
                    new_priority = max(1, min(5, int(new_priority_str)))  # Clamp priority between 1 and 5
                    return {"action": "set_priority", "task_time": task_time, "priority": new_priority}
                except ValueError:
                    return {"action": "unknown", "message": f"Invalid priority value '{new_priority_str}'. Use 1-5 after 'to' (e.g., 'set priority:14:30:00 to 3')!"}

        elif "complete task" in command and ":" in command:
            _, task_identifier = command.split(":", 1)
            return {"action": "complete", "identifier": task_identifier.strip()}

        elif "review completed" in command:
            return {"action": "review"}

        elif "list tasks" in command:
            return {"action": "list"}

        elif "clear tasks" in command:
            return {"action": "clear"}

        elif "exit" in command:
            return {"action": "exit"}

        return {"action": "unknown"}

    def respond(self, command):
        """Processes the parsed NLU result and generates a response."""
        nlu_result = self.parse_nlu(command)
        print(f"Responding to: {nlu_result}")  # Debugging output

        response_text = "..."  # Default, should be overwritten

        if nlu_result["action"] == "greet":
            self.state = "greeting"
            suggestion = self.suggest_task()
            response_text = f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"

        elif nlu_result["action"] == "add":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.tasks[timestamp] = nlu_result["desc"]
            self.task_history[nlu_result["desc"].lower()] += 1  # Update task frequency
            response_text = f"Yay! Added task: {nlu_result['desc']} at {timestamp}!"

        elif nlu_result["action"] == "schedule":
            try:
                today = datetime.now().date()
                scheduled_dt_candidate = datetime.strptime(nlu_result["time"], "%H:%M").time()
                scheduled_datetime = datetime.combine(today, scheduled_dt_candidate)
                if scheduled_datetime < datetime.now():
                    scheduled_datetime += timedelta(days=1)
                timestamp_key = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.scheduled_tasks[timestamp_key] = {
                    "desc": nlu_result["desc"],
                    "recurring": nlu_result["recurring"],
                    "priority": nlu_result["priority"]
                }
                response_text = f"Woo-hoo! Scheduled '{nlu_result['desc']}' (Priority: {nlu_result['priority']}) for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!"
            except ValueError:
                response_text = "Oops! Couldn’t process the scheduled time. Internal time format issue."

        elif nlu_result["action"] == "set_priority":
            task_time = nlu_result["task_time"]
            new_priority = nlu_result["priority"]
            found = False
            for timestamp in list(self.scheduled_tasks.keys()):
                if task_time in timestamp:
                    task_data = self.scheduled_tasks[timestamp]
                    task_data["priority"] = new_priority
                    response_text = f"Updated priority for '{task_data['desc']}' at {timestamp} to {new_priority}!"
                    found = True
                    break
            if not found:
                response_text = f"No scheduled task found with time '{task_time}'."

        elif nlu_result["action"] == "complete":
            task_identifier = nlu_result["identifier"].lower()
            found = False
            for timestamp in list(self.tasks.keys()):
                if task_identifier in timestamp.lower() or task_identifier in self.tasks[timestamp].lower():
                    desc = self.tasks.pop(timestamp)
                    self.completed_tasks[timestamp] = desc
                    self.task_history[desc.lower()] += 1  # Update task frequency
                    response_text = f"Great job! Marked '{desc}' ({timestamp}) as complete!"
                    found = True
                    break
            if not found:
                for timestamp in list(self.scheduled_tasks.keys()):
                    task_data = self.scheduled_tasks.get(timestamp)
                    if task_data and (task_identifier in timestamp.lower() or task_identifier in task_data["desc"].lower()):
                        desc = self.scheduled_tasks.pop(timestamp)["desc"]
                        self.completed_tasks[timestamp] = desc
                        self.task_history[desc.lower()] += 1  # Update task frequency
                        response_text = f"Great job! Marked '{desc}' ({timestamp}) as complete!"
                        found = True
                        break
            if not found:
                response_text = f"Task '{task_identifier}' not found in active or scheduled tasks."

        elif nlu_result["action"] == "review":
            if self.completed_tasks:
                response_text = "Completed tasks:\n" + "\n".join(f"- {t}: {d}" for t, d in self.completed_tasks.items())
            else:
                response_text = "No tasks completed yet!"

        elif nlu_result["action"] == "list":
            all_active_tasks = {**self.tasks, **{k: v["desc"] for k, v in self.scheduled_tasks.items()}}
            active_list = [f"- {t}: {v['desc']} (Priority: {v.get('priority', 1)})" for t, v in self.scheduled_tasks.items()] + \
                          [f"- {t}: {d}" for t, d in self.tasks.items()] if all_active_tasks else []
            completed_list = [f"- {t}: {d}" for t, d in sorted(self.completed_tasks.items())] if self.completed_tasks else []
            response_text = "Your tasks:\n" + "\n".join(sorted(active_list)) if active_list else ""
            if completed_list:
                response_text += "\nCompleted tasks:\n" + "\n".join(completed_list)
            if not active_list and not completed_list:
                response_text = "No tasks yet—give me something to do!"

        elif nlu_result["action"] == "clear":
            self.tasks.clear()
            self.scheduled_tasks.clear()
            self.completed_tasks.clear()
            self.task_history.clear()
            response_text = "All tasks cleared! I’m all fresh now!"

        elif nlu_result["action"] == "exit":
            self.state = "exiting"
            response_text = "Catch you later! Saving my notes..."

        elif nlu_result["action"] == "unknown":
            response_text = nlu_result.get("message", f"Oops! I’m puzzled. Try natural commands like ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘set priority:TIME to PRIORITY’, ‘complete task:TIME_OR_DESC’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’.")

        self._add_response_to_display(response_text)
        return response_text

    def suggest_task(self):
        """Provides a predictive task suggestion with prioritization."""
        current_time = datetime.now()
        suggestions = []
        for timestamp, task_data in self.scheduled_tasks.items():
            scheduled_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            time_diff = (scheduled_dt - current_time).total_seconds() / 60  # Difference in minutes
            if 0 < time_diff <= 120:  # Within the next 2 hours
                urgency = max(1, 120 - time_diff)  # Higher urgency for closer tasks
                priority_score = urgency * task_data["priority"]  # Combine urgency and priority
                suggestions.append((priority_score, f"Schedule {task_data['desc']} at {scheduled_dt.strftime('%H:%M')} (in {int(time_diff)} minutes, Priority: {task_data['priority']})"))
        if suggestions:
            suggestions.sort(reverse=True)  # Sort by priority score (highest first)
            return suggestions[0][1]  # Return highest priority suggestion

        # Predictive suggestion based on task history
        if self.task_history:
            most_frequent_task = max(self.task_history.items(), key=lambda x: x[1])[0]
            next_hour = (current_time.hour + 1) % 24
            suggested_time = current_time.replace(hour=next_hour, minute=0, second=0)
            if suggested_time < current_time:
                suggested_time += timedelta(days=1)
            return f"Based on your habits, how about scheduling {most_frequent_task} at {suggested_time.strftime('%H:%M')}?"
        current_hour = current_time.hour
        if 12 <= current_hour < 14:
            return "Perhaps it's time to schedule lunch around 12:30?"
        elif 17 <= current_hour < 19:
            return "Maybe schedule dinner prep for 17:30?"
        elif 21 <= current_hour < 23:
            return "Don't forget to schedule your bedtime routine around 22:00?"
        return "No specific suggestions right now—add your own task!"

    def visualize(self):
        """Renders the agent's state and text on the Pygame screen."""
        self.screen.fill(BACKGROUND_COLOR)

        # Draw agent "face" based on state
        agent_color = AGENT_COLOR_IDLE
        if self.state == "greeting":
            agent_color = AGENT_COLOR_GREETING
        elif self.state == "exiting":
            agent_color = AGENT_COLOR_EXITING
        elif self.state == "alert":
            agent_color = AGENT_COLOR_ALERT

        pygame.draw.circle(self.screen, agent_color, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3), 70)

        # Display response history
        y_offset = SCREEN_HEIGHT // 2 + 20
        for line_text in reversed(self.response_display):
            text_surface = self.font.render(line_text, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text_surface, text_rect.topleft)
            y_offset -= FONT_SIZE

        # Display input buffer at the bottom
        input_prompt = "You: " + self.input_buffer
        input_surface = self.font.render(input_prompt, True, TEXT_COLOR)
        self.screen.blit(input_surface, (10, SCREEN_HEIGHT - FONT_SIZE - 10))

        pygame.display.flip()

    def check_scheduled_tasks(self):
        """Checks for overdue scheduled tasks and triggers alerts."""
        current_datetime = datetime.now()
        for timestamp_key in list(self.scheduled_tasks.keys()):
            task_data = self.scheduled_tasks.get(timestamp_key)
            if not task_data:
                continue

            try:
                scheduled_dt = datetime.strptime(timestamp_key, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"Warning: Invalid timestamp format for '{timestamp_key}'. Removing task.")
                self.scheduled_tasks.pop(timestamp_key)
                continue

            current_minute = current_datetime.strftime("%Y-%m-%d %H:%M")
            if current_datetime >= scheduled_dt and current_minute not in self.last_notified.get(timestamp_key, []):
                try:
                    alert_message = f"⏰ Alert! Time to {task_data['desc']} at {scheduled_dt.strftime('%Y-%m-%d %H:%M')}"
                    self._add_response_to_display(alert_message)
                    print(alert_message)

                    self.state = "alert"
                    self.visualize()

                    if self.alert_sound:
                        self.alert_sound.play()
                    elif self.beep_sound:
                        self.beep_sound.play()
                    else:
                        print("No sound available—check sound files.")

                    self.last_notified[timestamp_key] = current_minute

                    if task_data["recurring"]:
                        new_scheduled_dt = scheduled_dt + timedelta(days=1)
                        new_timestamp_key = new_scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")
                        self.scheduled_tasks[new_timestamp_key] = task_data
                        print(f"Rescheduled recurring task '{task_data['desc']}' for {new_scheduled_dt.strftime('%Y-%m-%d %H:%M')}.")
                    else:
                        self.scheduled_tasks.pop(timestamp_key)
                        print(f"One-time task '{task_data['desc']}' completed and removed.")
                except Exception as e:
                    print(f"Error during alert processing for {timestamp_key} on line ~225: {e}")
                finally:
                    time.sleep(0.5)
                    self.state = "idle"
                    self.visualize()

    def run(self):
        """Main loop for the Chatty Agent."""
        running = True
        last_check_time = time.time()

        while running:
            current_loop_time = time.time()
            if current_loop_time - last_check_time >= CHECK_INTERVAL:
                self.check_scheduled_tasks()
                last_check_time = current_loop_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.input_buffer:
                            print(f"Processing input: '{self.input_buffer}'")
                            response = self.respond(self.input_buffer)
                            print(f"Agent says: {response}")
                            self.input_buffer = ""
                        self.visualize()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    elif event.unicode.isprintable():
                        self.input_buffer += event.unicode
                    self.visualize()

            pygame.time.delay(50)
            self.visualize()

        self._save_state()
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()