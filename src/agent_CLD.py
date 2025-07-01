import numpy as np
import pygame
import json
from datetime import datetime, timedelta
import os
import time
import random
import re
from dateutil.parser import parse

class ChattyAgent:
    def __init__(self):
        self.state = "idle"
        self.tasks = {}
        self.scheduled_tasks = {}
        self.completed_tasks = {}
        self.personality = "cheerful"
        self.input_buffer = ""
        self.task_counter = 0  # For unique task IDs
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption("Chatty Agent Task Manager")
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        
        # Track notifications to prevent duplicates
        self.notified_tasks = set()
        
        # Initialize sound system
        pygame.mixer.init()
        self.alert_sound = None
        self.beep_sound = None
        self.load_sounds()

    def load_sounds(self):
        """Load sound files with proper error handling"""
        try:
            if os.path.exists("alert.wav"):
                self.alert_sound = pygame.mixer.Sound("alert.wav")
            elif os.path.exists("beep.wav"):
                self.beep_sound = pygame.mixer.Sound("beep.wav")
            else:
                print("Info: No sound files found. Creating system beep sound.")
                # Create a simple beep sound programmatically
                self.create_beep_sound()
        except pygame.error as e:
            print(f"Warning: Could not load sound files: {e}")

    def create_beep_sound(self):
        """Create a simple beep sound programmatically"""
        try:
            # Create a simple sine wave beep
            sample_rate = 22050
            duration = 0.2
            frequency = 800
            
            frames = int(duration * sample_rate)
            arr = np.zeros((frames, 2))
            
            for i in range(frames):
                wave = np.sin(2 * np.pi * frequency * i / sample_rate)
                arr[i] = [wave * 0.3, wave * 0.3]  # Stereo, lower volume
            
            sound_array = (arr * 32767).astype(np.int16)
            self.beep_sound = pygame.sndarray.make_sound(sound_array)
        except Exception as e:
            print(f"Could not create beep sound: {e}")

    def parse_time(self, time_str):
        """Parse time string with better error handling"""
        time_str = time_str.strip().lower()
        
        # Try common time formats
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2})\.(\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                    
                    # Handle AM/PM
                    if len(match.groups()) > 2 and match.group(3):
                        if match.group(3) == 'pm' and hour != 12:
                            hour += 12
                        elif match.group(3) == 'am' and hour == 12:
                            hour = 0
                    
                    # Validate time
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                except (ValueError, IndexError):
                    continue
        
        # Try dateutil parser as fallback
        try:
            parsed = parse(time_str, fuzzy=True)
            return parsed.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        except:
            pass
        
        return None

    def parse_nlu(self, command):
        """Improved natural language understanding"""
        print(f"Parsing command: '{command}'")
        command = command.strip()
        command_lower = command.lower()
        
        # Greeting
        if any(word in command_lower for word in ["hello", "hi", "hey", "start"]):
            return {"action": "greet"}
        
        # Task operations
        if ":" in command:
            parts = command.split(":", 1)
            action_part = parts[0].strip().lower()
            content_part = parts[1].strip()
            
            if not content_part:
                return {"action": "error", "message": "Please provide content after the colon!"}
            
            # Add simple task
            if any(kw in action_part for kw in ["add task", "add", "task"]):
                return {"action": "add", "desc": content_part}
            
            # Schedule task
            elif any(kw in action_part for kw in ["schedule", "remind", "alert"]):
                # Look for time indicators
                time_indicators = [" at ", " for ", " in ", " on "]
                time_str = None
                desc = content_part
                
                for indicator in time_indicators:
                    if indicator in content_part.lower():
                        parts = content_part.lower().split(indicator, 1)
                        desc = parts[0].strip()
                        time_str = parts[1].strip()
                        break
                
                if time_str:
                    parsed_time = self.parse_time(time_str)
                    if parsed_time:
                        # If time is in the past, schedule for tomorrow
                        if parsed_time < datetime.now():
                            parsed_time += timedelta(days=1)
                        
                        recurring = "recurring" in action_part or "daily" in action_part
                        return {
                            "action": "schedule", 
                            "desc": desc, 
                            "time": parsed_time,
                            "recurring": recurring
                        }
                    else:
                        return {"action": "error", "message": f"Couldn't parse time '{time_str}'. Try formats like '2:30 PM' or '14:30'"}
                else:
                    return {"action": "add", "desc": desc}
            
            # Complete task
            elif any(kw in action_part for kw in ["complete", "done", "finish"]):
                return {"action": "complete", "task_id": content_part}
        
        # Commands without colons
        if "list" in command_lower or "show" in command_lower:
            return {"action": "list"}
        elif "clear" in command_lower:
            return {"action": "clear"}
        elif "review" in command_lower or "completed" in command_lower:
            return {"action": "review"}
        elif "exit" in command_lower or "quit" in command_lower:
            return {"action": "exit"}
        elif "help" in command_lower:
            return {"action": "help"}
        
        return {"action": "unknown"}

    def respond(self, command):
        """Process commands and return responses"""
        nlu_result = self.parse_nlu(command)
        print(f"Processing: {nlu_result}")
        
        if nlu_result["action"] == "greet":
            self.state = "greeting"
            suggestion = self.suggest_task()
            return f"Hey there! I'm your {self.personality} task assistant! 🎉 {suggestion}"
        
        elif nlu_result["action"] == "add":
            self.task_counter += 1
            task_id = f"task_{self.task_counter}"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.tasks[task_id] = {
                "desc": nlu_result["desc"],
                "created": timestamp,
                "id": task_id
            }
            return f"✅ Added task '{nlu_result['desc']}' (ID: {task_id})"
        
        elif nlu_result["action"] == "schedule":
            self.task_counter += 1
            task_id = f"sched_{self.task_counter}"
            schedule_time = nlu_result["time"]
            
            # Ensure schedule_time is a datetime object
            if isinstance(schedule_time, str):
                schedule_time = self.parse_time(schedule_time)
                if not schedule_time:
                    return "❌ Invalid time format. Please try again with a format like '2:30 PM' or '14:30'"
            
            self.scheduled_tasks[task_id] = {
                "desc": nlu_result["desc"],
                "time": schedule_time,
                "recurring": nlu_result["recurring"],
                "id": task_id,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            time_str = schedule_time.strftime("%I:%M %p on %B %d")
            recurring_str = " (recurring daily)" if nlu_result["recurring"] else ""
            return f"⏰ Scheduled '{nlu_result['desc']}' for {time_str}{recurring_str} (ID: {task_id})"
        
        elif nlu_result["action"] == "complete":
            task_id = nlu_result["task_id"]
            
            # Try to find task by ID or partial description
            found_task = None
            found_in = None
            
            # Check regular tasks
            for tid, task in self.tasks.items():
                if tid == task_id or task_id.lower() in task["desc"].lower():
                    found_task = task
                    found_in = "tasks"
                    break
            
            # Check scheduled tasks if not found
            if not found_task:
                for tid, task in self.scheduled_tasks.items():
                    if tid == task_id or task_id.lower() in task["desc"].lower():
                        found_task = task
                        found_in = "scheduled"
                        break
            
            if found_task:
                # Move to completed
                completed_id = found_task["id"]
                self.completed_tasks[completed_id] = {
                    **found_task,
                    "completed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Remove from original location
                if found_in == "tasks":
                    self.tasks.pop(found_task["id"])
                else:
                    self.scheduled_tasks.pop(found_task["id"])
                
                return f"🎉 Completed task '{found_task['desc']}'!"
            else:
                return f"❌ Task '{task_id}' not found. Use 'list' to see available tasks."
        
        elif nlu_result["action"] == "list":
            response = "📋 **Your Tasks:**\n\n"
            
            if self.tasks:
                response += "**Regular Tasks:**\n"
                for task_id, task in self.tasks.items():
                    response += f"• {task['desc']} (ID: {task_id})\n"
                response += "\n"
            
            if self.scheduled_tasks:
                response += "**Scheduled Tasks:**\n"
                for task_id, task in self.scheduled_tasks.items():
                    time_str = task['time'].strftime("%I:%M %p on %b %d")
                    recurring = " [Daily]" if task['recurring'] else ""
                    response += f"• {task['desc']} - {time_str}{recurring} (ID: {task_id})\n"
                response += "\n"
            
            if self.completed_tasks:
                response += f"**Completed Tasks:** {len(self.completed_tasks)} total\n"
            
            if not self.tasks and not self.scheduled_tasks:
                response += "No active tasks! Add some with 'add task:description' or 'schedule:description at time'"
            
            return response
        
        elif nlu_result["action"] == "review":
            if not self.completed_tasks:
                return "📝 No completed tasks yet!"
            
            response = "🏆 **Completed Tasks:**\n\n"
            for task_id, task in self.completed_tasks.items():
                completed_time = task.get("completed", "Unknown time")
                response += f"• {task['desc']} - Completed: {completed_time}\n"
            
            return response
        
        elif nlu_result["action"] == "clear":
            cleared_count = len(self.tasks) + len(self.scheduled_tasks)
            self.tasks.clear()
            self.scheduled_tasks.clear()
            self.notified_tasks.clear()
            return f"🧹 Cleared {cleared_count} tasks! Starting fresh!"
        
        elif nlu_result["action"] == "help":
            return """🤖 **Chatty Agent Commands:**

• **hello** - Greet me!
• **add task:description** - Add a simple task
• **schedule:description at time** - Schedule a task (e.g., "schedule:meeting at 2:30 PM")
• **schedule recurring:description at time** - Daily recurring task
• **complete:task_id** - Mark task as complete
• **list** - Show all tasks
• **review** - Show completed tasks
• **clear** - Clear all tasks
• **exit** - Save and quit

**Time formats:** 2:30 PM, 14:30, 2:30, etc.
**Examples:** 
- schedule:lunch at 12:30 PM
- add task:buy groceries
- complete:task_1"""
        
        elif nlu_result["action"] == "exit":
            self.state = "exiting"
            return "👋 Goodbye! Saving your tasks..."
        
        elif nlu_result["action"] == "error":
            return f"❌ {nlu_result['message']}"
        
        else:
            return """🤔 I didn't understand that. Try:
• **add task:description** - Add a task
• **schedule:description at time** - Schedule a task
• **list** - Show tasks
• **help** - Show all commands"""

    def suggest_task(self):
        """Suggest tasks based on time of day"""
        current_hour = datetime.now().hour
        
        suggestions = {
            (6, 9): "How about 'schedule:morning coffee at 8:00 AM'?",
            (11, 13): "Maybe 'schedule:lunch break at 12:30 PM'?",
            (14, 16): "Consider 'schedule:afternoon break at 3:00 PM'?",
            (17, 19): "How about 'schedule:dinner prep at 6:00 PM'?",
            (20, 22): "Maybe 'schedule:evening wind-down at 9:00 PM'?"
        }
        
        for (start, end), suggestion in suggestions.items():
            if start <= current_hour < end:
                return suggestion
        
        return "Type 'help' to see what I can do!"

    def visualize(self):
        """Improved visualization"""
        self.screen.fill((20, 20, 30))  # Dark blue background
        
        # Title
        title = self.title_font.render("🤖 Chatty Agent", True, (100, 200, 255))
        self.screen.blit(title, (10, 10))
        
        # Status indicator
        status_color = {
            "idle": (100, 100, 100),
            "greeting": (100, 255, 100),
            "exiting": (255, 100, 100)
        }.get(self.state, (255, 255, 255))
        
        pygame.draw.circle(self.screen, status_color, (550, 30), 20)
        
        # Task counts
        task_count = len(self.tasks) + len(self.scheduled_tasks)
        completed_count = len(self.completed_tasks)
        
        counts_text = f"Active: {task_count} | Completed: {completed_count}"
        counts_surface = self.font.render(counts_text, True, (200, 200, 200))
        self.screen.blit(counts_surface, (10, 50))
        
        # Input field
        input_bg = pygame.Rect(10, 320, 580, 30)
        pygame.draw.rect(self.screen, (40, 40, 60), input_bg)
        pygame.draw.rect(self.screen, (100, 100, 150), input_bg, 2)
        
        prompt = "Type command: "
        input_text = prompt + self.input_buffer + "_"
        input_surface = self.font.render(input_text, True, (255, 255, 255))
        self.screen.blit(input_surface, (15, 325))
        
        # Help text
        help_text = "Commands: add task:desc | schedule:desc at time | list | help | exit"
        help_surface = self.font.render(help_text, True, (150, 150, 150))
        self.screen.blit(help_surface, (10, 360))
        
        pygame.display.flip()

    def check_scheduled_tasks(self):
        """Check for scheduled tasks that need alerts"""
        current_time = datetime.now()
        
        for task_id, task in list(self.scheduled_tasks.items()):
            scheduled_time = task["time"]
            
            # Check if it's time for the task (within 1 minute)
            time_diff = (current_time - scheduled_time).total_seconds()
            
            if 0 <= time_diff <= 60 and task_id not in self.notified_tasks:
                # Trigger alert
                print(f"⏰ ALERT! Time for: {task['desc']}")
                
                # Play sound
                if self.alert_sound:
                    self.alert_sound.play()
                elif self.beep_sound:
                    self.beep_sound.play()
                
                # Visual alert
                self.state = "greeting"
                
                # Mark as notified
                self.notified_tasks.add(task_id)
                
                # Handle recurring tasks
                if task["recurring"]:
                    # Schedule for next day
                    next_time = scheduled_time + timedelta(days=1)
                    self.task_counter += 1
                    new_task_id = f"sched_{self.task_counter}"
                    
                    self.scheduled_tasks[new_task_id] = {
                        **task,
                        "time": next_time,
                        "id": new_task_id
                    }
                
                # Remove original task
                del self.scheduled_tasks[task_id]

    def save_data(self):
        """Save tasks to file"""
        os.makedirs("data", exist_ok=True)
        
        # Convert datetime objects to strings for JSON serialization
        data = {
            "tasks": self.tasks,
            "scheduled_tasks": {},
            "completed_tasks": self.completed_tasks,
            "task_counter": self.task_counter
        }
        
        # Convert scheduled tasks times to strings
        for task_id, task in self.scheduled_tasks.items():
            data["scheduled_tasks"][task_id] = {
                **task,
                "time": task["time"].isoformat()
            }
        
        with open("data/tasks.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        print("💾 Tasks saved successfully!")

    def load_data(self):
        """Load tasks from file"""
        if os.path.exists("data/tasks.json"):
            try:
                with open("data/tasks.json", "r") as f:
                    data = json.load(f)
                
                self.tasks = data.get("tasks", {})
                self.completed_tasks = data.get("completed_tasks", {})
                self.task_counter = data.get("task_counter", 0)
                
                # Convert scheduled tasks times back to datetime objects
                scheduled_data = data.get("scheduled_tasks", {})
                for task_id, task in scheduled_data.items():
                    task["time"] = datetime.fromisoformat(task["time"])
                    self.scheduled_tasks[task_id] = task
                
                print("📂 Tasks loaded successfully!")
            except Exception as e:
                print(f"⚠️ Error loading tasks: {e}")

    def run(self):
        """Main game loop"""
        print("🚀 Starting Chatty Agent...")
        self.load_data()
        
        running = True
        clock = pygame.time.Clock()
        
        while running:
            # Check for scheduled task alerts
            self.check_scheduled_tasks()
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.input_buffer:
                            print(f"\n>>> {self.input_buffer}")
                            response = self.respond(self.input_buffer)
                            print(f"🤖 {response}\n")
                            
                            if self.state == "exiting":
                                running = False
                            
                            self.input_buffer = ""
                    
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    
                    elif event.unicode.isprintable():
                        self.input_buffer += event.unicode
            
            # Update display
            self.visualize()
            clock.tick(60)  # 60 FPS
        
        # Save data before exiting
        self.save_data()
        pygame.quit()
        print("👋 Goodbye!")

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()