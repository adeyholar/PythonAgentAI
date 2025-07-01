# chatty_agent.py
import pygame
import time
import threading
from datetime import datetime, timedelta

# Import all necessary components and constants
from task_manager import TaskManager
from nlu_parser import NLUParser
from external_services import OllamaClient, EmailClient
from ui_manager import UIManager
from config import CHECK_INTERVAL, BLOG_INTERVAL, ALERT_SOUND_FILE, BEEP_SOUND_FILE, SCREEN_WIDTH, SCREEN_HEIGHT, TASKS_FILE # Import SCREEN_WIDTH, SCREEN_HEIGHT from config

class ChattyAgent:
    def __init__(self):
        pygame.init()  # Ensure Pygame is initialized first
        pygame.mixer.init()  # Explicitly initialize mixer

        self.task_manager = TaskManager()
        self.nlu = NLUParser()
        self.ollama_client = OllamaClient()
        self.email_client = EmailClient()

        # Initialize Pygame display here, and then pass the screen surface to UIManager
        initial_screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Chatty Agent")
        
        # UIManager now takes the screen directly in its constructor or via a dedicated setter
        # Let's refactor UIManager to accept screen in __init__ or have a simple set_screen
        self.ui = UIManager(initial_screen) # Pass initial_screen to UIManager constructor
        
        self.state = "idle" # Overall agent state (for visual feedback)
        self.personality = "cheerful"
        self.last_check_time = time.time() # For periodic task checks

        self.alert_sound = self._load_sound(ALERT_SOUND_FILE)
        self.beep_sound = self._load_sound(BEEP_SOUND_FILE)
        if not self.alert_sound or not self.beep_sound:
            print("Warning: Sound files may not load correctly. Ensure 'alert.wav' and 'beep.wav' exist.")

        # Load initial state for tasks
        self.task_manager.load_state(TASKS_FILE)

        # Start background blog generation thread
        blog_thread = threading.Thread(target=self._schedule_blog_generation, daemon=True)
        blog_thread.start()

        # Initial visualization (draw empty screen + agent)
        self.ui.visualize(self.state) # ui.visualize now takes only state

    def _load_sound(self, filename):
        try:
            return pygame.mixer.Sound(filename)
        except pygame.error as e:
            print(f"Warning: Could not load sound file '{filename}': {e}")
            return None

    def _schedule_blog_generation(self):
        """Schedules blog generation and email at regular intervals."""
        while True:
            # Calculate time to wait until the next interval
            now = datetime.now()
            next_interval_time = now + timedelta(seconds=BLOG_INTERVAL)
            time_to_wait = (next_interval_time - now).total_seconds()
            if time_to_wait < 0: # If somehow we are behind schedule, just wait for next full interval
                time_to_wait = 0 # Or could be BLOG_INTERVAL - (abs(time_to_wait) % BLOG_INTERVAL)

            time.sleep(max(0, time_to_wait)) # Ensure non-negative wait time

            blog_content = self.ollama_client.generate_blog() # Use default prompt or pass a specific one
            subject = f"Blog Post - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.email_client.send_email(subject, blog_content)
            self.ui.add_response(f"Blog generated and emailed at {datetime.now().strftime('%H:%M')}")

    def respond(self, command):
        """Processes a user command and returns a response."""
        nlu_result = self.nlu.parse(command)
        response_text = "..." # Default response, should be overwritten

        action = nlu_result["action"]
        
        if action == "greet":
            self.state = "greeting"
            # TaskManager now handles suggestion logic
            suggestion = self.task_manager.suggest_task() 
            response_text = f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"
        
        elif action == "add":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # TaskManager returns the full response string
            response_text = self.task_manager.add_task(nlu_result["desc"], timestamp) 
        
        elif action == "schedule":
            try:
                today = datetime.now().date()
                scheduled_dt_candidate = datetime.strptime(nlu_result["time"], "%H:%M").time()
                scheduled_datetime = datetime.combine(today, scheduled_dt_candidate)
                # If scheduled time is in the past for today, schedule for next day
                if scheduled_datetime < datetime.now():
                    scheduled_datetime += timedelta(days=1)
                # TaskManager returns the full response string
                response_text = self.task_manager.schedule_task(
                    nlu_result["desc"], scheduled_datetime, nlu_result["recurring"], nlu_result["priority"]
                )
            except ValueError:
                response_text = "Oops! Couldn’t process the scheduled time. Please use a valid time format (e.g., '14:30' or '2:30 PM')."
            
        elif action == "set_priority":
            # TaskManager returns description and timestamp, ChattyAgent formats response
            desc, timestamp = self.task_manager.set_priority(nlu_result["task_time"], nlu_result["priority"])
            response_text = f"Updated priority for '{desc}' at {timestamp} to {nlu_result['priority']}!" if desc else f"No scheduled task found matching '{nlu_result['task_time']}'."
            
        elif action == "feedback":
            # Explicitly cast to int to help Pylance
            self.task_manager.feedback_history[nlu_result["suggestion"].lower()] += int(nlu_result["feedback"]) # FIX: Explicit cast to int
            feedback_value_str = "good" if nlu_result["feedback"] == 1 else "bad" if nlu_result["feedback"] == -1 else "neutral"
            response_text = f"Feedback recorded for '{nlu_result['suggestion']}': {feedback_value_str}"

        elif action == "generate_blog":
            blog_content = self.ollama_client.generate_blog()
            subject = f"Blog Post - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.email_client.send_email(subject, blog_content)
            # Add detailed blog content to response display
            self.ui.add_response(f"Generated and emailed blog post: {subject}\n{blog_content[:100]}...") 
            # Provide a concise response for the input line
            response_text = "Blog generated and emailed!" 

        elif action == "complete":
            # TaskManager returns description and timestamp, ChattyAgent formats response
            desc, timestamp = self.task_manager.complete_task(nlu_result["identifier"])
            response_text = f"Great job! Marked '{desc}' ({timestamp}) as complete!" if desc else f"Task '{nlu_result['identifier']}' not found in active or scheduled tasks."
        
        elif action == "review":
            # TaskManager returns the formatted string
            response_text = self.task_manager.get_completed_tasks_display()
        
        elif action == "list":
            # TaskManager returns the formatted string
            response_text = self.task_manager.get_all_tasks_display()
        
        elif action == "clear":
            self.task_manager.clear_tasks() # TaskManager clears its data
            response_text = "All tasks cleared! I’m all fresh now!" # ChattyAgent provides generic response

        elif action == "exit":
            self.state = "exiting"
            response_text = "Catch you later! Saving my notes..."
        
        elif action == "unknown":
            response_text = nlu_result.get("message", "Oops! I’m puzzled. Try natural commands like ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘set priority:TIME to PRIORITY’, ‘feedback:SUGGESTION on LIKE/DISLIKE’, ‘generate blog’, ‘complete task:TIME_OR_DESC’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’.")

        self.ui.add_response(response_text) # Add agent's response to UI display
        return response_text

    def check_scheduled_tasks_and_notify_ui(self):
        """
        Delegates task checking to TaskManager and handles UI alerts/sounds based on results.
        """
        alerts = self.task_manager.check_and_update_scheduled_tasks() # TaskManager returns list of alert messages
        if alerts:
            self.state = "alert" # Set agent state to alert for visual feedback
            for alert_message in alerts:
                self.ui.add_response(alert_message) # Add each alert message to UI display
                print(alert_message) # Also print to console for debugging
            
            # Play sound based on availability
            if self.alert_sound:
                self.alert_sound.play()
            elif self.beep_sound:
                self.beep_sound.play()
            else:
                print("No sound available—check sound files.") # Fallback message

            # Briefly show alert state, then revert to idle
            self.ui.visualize(self.state) # Update UI to show alert state
            time.sleep(0.5) # Short delay
            self.state = "idle" # Revert agent state
            self.ui.visualize(self.state) # Update UI to show idle state

    def run(self):
        running = True
        
        while running:
            # Periodic check for scheduled tasks
            current_loop_time = time.time()
            if current_loop_time - self.last_check_time >= CHECK_INTERVAL:
                self.check_scheduled_tasks_and_notify_ui() # Call the unified method
                self.last_check_time = current_loop_time

            # Event handling (Pygame events)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    # When window is resized, update the Pygame display mode
                    # And pass the new screen surface to the UIManager
                    current_screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.ui.set_screen(current_screen) # FIX: Use UIManager's set_screen method
                    self.ui.visualize(self.state) # Re-render with new dimensions
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        current_input = self.ui.get_input_buffer() # Get input from UI manager
                        if current_input:
                            print(f"Processing input: '{current_input}'")
                            response = self.respond(current_input) # Process command
                            print(f"Agent says: {response}")
                            self.ui.clear_input_buffer() # Clear input buffer via UI manager
                        self.ui.visualize(self.state) # Visualize after input processing
                    elif event.key == pygame.K_BACKSPACE:
                        self.ui.remove_from_input_buffer() # Remove char via UI manager
                        self.ui.visualize(self.state)
                    elif event.key == pygame.K_e:
                        self.ui.toggle_expanded() # Toggle expanded flag in UI manager
                        # Based on the expanded state, adjust window size
                        width, height = (1200, 900) if self.ui.expanded else (SCREEN_WIDTH, SCREEN_HEIGHT)
                        
                        # Re-create screen and update UIManager
                        current_screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                        self.ui.set_screen(current_screen) # Update UIManager's screen
                        
                        self.ui.visualize(self.state) # Re-visualize after resize/expand
                    elif event.unicode.isprintable():
                        self.ui.add_to_input_buffer(event.unicode) # Add char via UI manager
                        self.ui.visualize(self.state)

            pygame.time.delay(50) # Small delay to prevent 100% CPU usage
            self.ui.visualize(self.state) # Always visualize at the end of the loop iteration

        self.task_manager.save_state(TASKS_FILE) # Save all task data before exiting
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()