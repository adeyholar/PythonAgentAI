import numpy as np # Not directly used in the current logic, consider removing if not planning future use
import pygame
import json
from datetime import datetime, timedelta
import os
import time
import random
from dateutil.parser import parse, ParserError # Import ParserError for better error handling

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
AGENT_COLOR_IDLE = (0, 200, 255) # Light Blue
AGENT_COLOR_GREETING = (0, 255, 0) # Green
AGENT_COLOR_EXITING = (255, 0, 0) # Red
AGENT_COLOR_ALERT = (255, 165, 0) # Orange for alerts

class ChattyAgent:
    def __init__(self):
        # --- Agent State & Data ---
        self.state = "idle" # Current visual/functional state (idle, greeting, exiting, alert)
        self.tasks = {} # General tasks (timestamp: desc)
        self.scheduled_tasks = {} # Scheduled tasks (timestamp: {"desc": ..., "recurring": ...})
        self.completed_tasks = {} # Completed tasks (timestamp: desc)
        self.personality = "cheerful"
        
        # --- UI Components ---
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Chatty Agent")
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.input_buffer = ""
        self.response_display = [] # Stores recent responses for display
        self.max_response_lines = 10 # Max lines to show in response area

        # --- Sound Components ---
        pygame.mixer.init()
        self.alert_sound = self._load_sound(ALERT_SOUND_FILE)
        self.beep_sound = self._load_sound(BEEP_SOUND_FILE)
        self.last_notified = {} # Track last notification time per task to avoid spamming

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
        """Loads tasks, scheduled_tasks, and completed_tasks from JSON file."""
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", {})
                    self.scheduled_tasks = data.get("scheduled_tasks", {})
                    self.completed_tasks = data.get("completed_tasks", {})
                print(f"Loaded tasks from {TASKS_FILE}")
            except json.JSONDecodeError as e:
                print(f"Error loading tasks from {TASKS_FILE}: Invalid JSON. Starting fresh. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while loading tasks: {e}. Starting fresh.")
        else:
            print(f"No existing task file found at {TASKS_FILE}. Starting fresh.")
    
    def _save_state(self):
        """Saves current task state to JSON file."""
        os.makedirs(DATA_DIR, exist_ok=True) # Ensure data directory exists
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "tasks": self.tasks,
                    "scheduled_tasks": self.scheduled_tasks,
                    "completed_tasks": self.completed_tasks
                }, f, indent=4)
            print(f"Saved tasks to {TASKS_FILE}")
        except Exception as e:
            print(f"Error saving tasks to {TASKS_FILE}: {e}")

    def _add_response_to_display(self, response):
        """Adds a response string to the display buffer, splitting into lines."""
        for line in response.split('\n'):
            self.response_display.append(line)
        # Keep only the most recent lines
        if len(self.response_display) > self.max_response_lines:
            self.response_display = self.response_display[-self.max_response_lines:]

    def parse_nlu(self, command):
        """Parses user command to determine action and extract entities."""
        print(f"Parsing command: '{command}'") # Debugging output
        command = command.lower().strip()

        if "hello" in command:
            return {"action": "greet"}
        
        elif "add task" in command and ":" in command:
            parts = command.split(":", 1)
            desc = parts[1].strip()
            if not desc:
                return {"action": "unknown", "message": "Please provide a task description after 'add task:'!"}
            return {"action": "add", "desc": desc}

        elif any(kw in command for kw in ["schedule task", "schedule recurring"]) and ":" in command:
            parts = command.split(":", 1)
            action_part = parts[0].strip()
            # Try to find ' at ', ' for ', ' in ' to separate description from time
            desc_time_parts = parts[1].split(" at ", 1)
            if len(desc_time_parts) > 1:
                desc = desc_time_parts[0].strip()
                time_str = desc_time_parts[1].strip()
            else: # No ' at ', check ' for ' or ' in '
                desc_time_parts = parts[1].split(" for ", 1)
                if len(desc_time_parts) > 1:
                    desc = desc_time_parts[0].strip()
                    time_str = desc_time_parts[1].strip()
                else:
                    desc_time_parts = parts[1].split(" in ", 1)
                    if len(desc_time_parts) > 1:
                        desc = desc_time_parts[0].strip()
                        time_str = desc_time_parts[1].strip()
                    else: # No time keyword found, assume entire part after ':' is desc
                        desc = parts[1].strip()
                        time_str = "" # No explicit time string found
            
            if not desc:
                return {"action": "unknown", "message": f"Please provide a task description after '{action_part}:' (e.g., 'schedule task:check desk at 1:15')!"}
            
            if not time_str:
                 return {"action": "unknown", "message": f"Please specify a time for the scheduled task (e.g., 'schedule task:{desc} at 1:15')!"}

            try:
                # Use fuzzy=True for more lenient parsing (e.g., "1pm", "five past two")
                parsed_time = parse(time_str, fuzzy=True)
                # Format to HH:MM to store consistently
                time_match = parsed_time.strftime("%H:%M")
                recurring = "recurring" in command
                return {"action": "schedule", "desc": desc, "time": time_match, "recurring": recurring}
            except ParserError:
                return {"action": "unknown", "message": f"Couldn’t understand the time '{time_str}'. Please use formats like '1:15 PM', '13:00', 'noon'."}
        
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
        print(f"Responding to: {nlu_result}") # Debugging output
        
        response_text = "..." # Default, should be overwritten

        if nlu_result["action"] == "greet":
            self.state = "greeting"
            suggestion = self.suggest_task()
            response_text = f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"
        
        elif nlu_result["action"] == "add":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # More precise timestamp
            self.tasks[timestamp] = nlu_result["desc"]
            response_text = f"Yay! Added task: {nlu_result['desc']} at {timestamp}!"
        
        elif nlu_result["action"] == "schedule":
            try:
                # Combine today's date with the parsed time
                today = datetime.now().date()
                scheduled_dt_candidate = datetime.strptime(nlu_result["time"], "%H:%M").time()
                scheduled_datetime = datetime.combine(today, scheduled_dt_candidate)

                # If scheduled time is in the past, schedule for tomorrow
                if scheduled_datetime < datetime.now():
                    scheduled_datetime += timedelta(days=1)
                
                timestamp_key = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S") # Use full datetime as key
                self.scheduled_tasks[timestamp_key] = {"desc": nlu_result["desc"], "recurring": nlu_result["recurring"]}
                response_text = f"Woo-hoo! Scheduled '{nlu_result['desc']}' for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!"
            except ValueError:
                response_text = "Oops! Couldn’t process the scheduled time. Internal time format issue."
        
        elif nlu_result["action"] == "complete":
            task_identifier = nlu_result["identifier"].lower()
            found = False
            
            # Search in general tasks
            for timestamp in list(self.tasks.keys()):
                if task_identifier in timestamp.lower() or task_identifier in self.tasks[timestamp].lower():
                    desc = self.tasks.pop(timestamp)
                    self.completed_tasks[timestamp] = desc
                    response_text = f"Great job! Marked '{desc}' ({timestamp}) as complete!"
                    found = True
                    break
            
            # If not found, search in scheduled tasks
            if not found:
                for timestamp in list(self.scheduled_tasks.keys()):
                    task_data = self.scheduled_tasks.get(timestamp)
                    if task_data and (task_identifier in timestamp.lower() or task_identifier in task_data["desc"].lower()):
                        desc = self.scheduled_tasks.pop(timestamp)["desc"]
                        self.completed_tasks[timestamp] = desc
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
            
            active_list = []
            if all_active_tasks:
                active_list = [f"- {t}: {d}" for t, d in sorted(all_active_tasks.items())]

            completed_list = []
            if self.completed_tasks:
                completed_list = [f"- {t}: {d}" for t, d in sorted(self.completed_tasks.items())]

            if active_list or completed_list:
                response_text = "Your tasks:\n" + "\n".join(active_list) if active_list else ""
                if completed_list:
                    response_text += "\nCompleted tasks:\n" + "\n".join(completed_list)
            else:
                response_text = "No tasks yet—give me something to do!"
        
        elif nlu_result["action"] == "clear":
            self.tasks.clear()
            self.scheduled_tasks.clear()
            self.completed_tasks.clear()
            response_text = "All tasks cleared! I’m all fresh now!"
        
        elif nlu_result["action"] == "exit":
            self.state = "exiting"
            response_text = "Catch you later! Saving my notes..."
        
        elif nlu_result["action"] == "unknown":
            response_text = nlu_result.get("message", f"Oops! I’m puzzled. Try natural commands like ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘complete task:TIME_OR_DESC’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’.")

        self._add_response_to_display(response_text) # Add response to internal display buffer
        return response_text # Also return for console logging if desired

    def suggest_task(self):
        """Provides a time-based task suggestion."""
        current_hour = datetime.now().hour
        if 8 <= current_hour < 10:
            return "How about scheduling your morning coffee break around 9:00?"
        elif 12 <= current_hour < 14:
            return "Perhaps it's time to schedule lunch around 12:30?"
        elif 17 <= current_hour < 19:
            return "Maybe schedule dinner prep for 17:30?"
        elif 21 <= current_hour < 23:
            return "Don't forget to schedule your bedtime routine around 22:00!"
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
        for line_text in reversed(self.response_display): # Show most recent at bottom
            text_surface = self.font.render(line_text, True, TEXT_COLOR)
            # Center the response text roughly
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text_surface, text_rect.topleft)
            y_offset -= FONT_SIZE # Move up for next line

        # Display input buffer at the bottom
        input_prompt = "You: " + self.input_buffer
        input_surface = self.font.render(input_prompt, True, TEXT_COLOR)
        self.screen.blit(input_surface, (10, SCREEN_HEIGHT - FONT_SIZE - 10))

        pygame.display.flip()

    def check_scheduled_tasks(self):
        """Checks for overdue scheduled tasks and triggers alerts."""
        current_datetime = datetime.now()
        # Create a list of keys to avoid modifying dict during iteration
        for timestamp_key in list(self.scheduled_tasks.keys()):
            task_data = self.scheduled_tasks.get(timestamp_key)
            if not task_data: # Task might have been popped by another check
                continue

            try:
                scheduled_dt = datetime.strptime(timestamp_key, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"Warning: Invalid timestamp format in scheduled_tasks for key '{timestamp_key}'. Removing task.")
                self.scheduled_tasks.pop(timestamp_key)
                continue

            # Check if current time is past or at the scheduled time
            # And prevent multiple notifications for the same minute for non-recurring tasks
            # For recurring, we allow one notification per day for that task.
            notification_key = scheduled_dt.strftime("%H:%M") # Track notification per minute
            
            # This logic needs careful refinement based on how recurring notifications should behave.
            # Current logic: Notify once per minute for any task. For recurring, re-schedule for next day.
            # Let's adjust to ensure recurring tasks notify once per day, and non-recurring once ever.

            if current_datetime >= scheduled_dt:
                # Check if we've already notified for this task at this specific minute today
                # This prevents notification every second within the same minute.
                already_notified_today_minute = self.last_notified.get(timestamp_key) == current_datetime.strftime("%Y-%m-%d %H:%M")

                if not already_notified_today_minute:
                    alert_message = f"⏰ Alert! Time to {task_data['desc']}!"
                    self._add_response_to_display(alert_message)
                    print(alert_message)
                    
                    self.state = "alert" # Change state for visual feedback
                    self.visualize()
                    
                    if self.alert_sound:
                        self.alert_sound.play()
                    elif self.beep_sound:
                        self.beep_sound.play()
                    else:
                        print("No sound available—check sound files.")
                    
                    # Store notification time
                    self.last_notified[timestamp_key] = current_datetime.strftime("%Y-%m-%d %H:%M")

                    # Handle recurring vs. one-time tasks
                    if task_data["recurring"]:
                        # Reschedule for the same time tomorrow
                        new_scheduled_dt = scheduled_dt + timedelta(days=1)
                        new_timestamp_key = new_scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")
                        self.scheduled_tasks[new_timestamp_key] = self.scheduled_tasks.pop(timestamp_key)
                        print(f"Rescheduled recurring task '{task_data['desc']}' for {new_scheduled_dt.strftime('%Y-%m-%d %H:%M')}.")
                    else:
                        # Move to completed tasks (or simply remove if not needed in completed for one-time alerts)
                        # For now, let's just remove it if it's a one-time alert.
                        # If you want to move to completed, you'd do:
                        # self.completed_tasks[timestamp_key] = task_data["desc"]
                        self.scheduled_tasks.pop(timestamp_key)
                        print(f"One-time task '{task_data['desc']}' completed and removed from schedule.")
                    
                    time.sleep(0.5) # Small delay for sound to play and visual update
                    self.state = "idle" # Return to idle after alert
                    self.visualize() # Update visualization immediately

    def run(self):
        """Main loop for the Chatty Agent."""
        running = True
        last_check_time = time.time() # To control frequency of task checks

        while running:
            # Check scheduled tasks at a reasonable interval (e.g., every 1 second)
            current_loop_time = time.time()
            if current_loop_time - last_check_time >= 1: # Check every second
                self.check_scheduled_tasks()
                last_check_time = current_loop_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.input_buffer: # Only process if there's input
                            print(f"Processing input: '{self.input_buffer}'")
                            response = self.respond(self.input_buffer)
                            print(f"Agent says: {response}") # Log agent's full response
                            self.input_buffer = ""
                        self.visualize() # Update visualization after processing command
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    elif event.unicode.isprintable():
                        self.input_buffer += event.unicode
                    self.visualize() # Update visualization for every key press

            # Small delay to prevent 100% CPU usage
            pygame.time.delay(50) 
            self.visualize() # Keep visualizing to show input buffer changes

        self._save_state() # Save state before exiting
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()