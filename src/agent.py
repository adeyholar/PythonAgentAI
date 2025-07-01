import numpy as np
import pygame
import json
from datetime import datetime, timedelta
import os
import time
import random
from dateutil.parser import parse  # For flexible time parsing

class ChattyAgent:
    def __init__(self):
        self.state = "idle"
        self.tasks = {}
        self.scheduled_tasks = {}
        self.completed_tasks = {}
        self.personality = "cheerful"
        self.input_buffer = ""
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Chatty Agent")
        self.font = pygame.font.Font(None, 36)
        self.last_notified = {}  # Track last notification time per task
        pygame.mixer.init()
        self.alert_sound = None
        self.beep_sound = None
        try:
            self.alert_sound = pygame.mixer.Sound("alert.wav")
            self.beep_sound = pygame.mixer.Sound("beep.wav")
        except pygame.error:
            print("Warning: Could not load sound files. Notifications will be silent.")

    def parse_nlu(self, command):
        command = command.lower().strip()
        if "hello" in command:
            return {"action": "greet"}
        elif any(kw in command for kw in ["add task", "schedule task", "schedule recurring"]):
            if ":" in command:
                parts = command.split(":", 1)
                desc = parts[0].replace("add task", "").replace("schedule task", "").replace("schedule recurring", "").strip()
                if not desc:
                    return {"action": "unknown", "message": "Please provide a task description!"}
                time_match = None
                for t in ["at", "for", "in"]:
                    if t in command:
                        time_str = command.split(t)[1].strip()
                        try:
                            time_match = parse(time_str, fuzzy=True).strftime("%H:%M")
                            break
                        except ValueError:
                            continue
                if time_match:
                    recurring = "recurring" in command
                    return {"action": "schedule", "desc": desc, "time": time_match, "recurring": recurring}
                return {"action": "add", "desc": desc}
        elif "complete task" in command and ":" in command:
            _, task_time = command.split(":", 1)
            return {"action": "complete", "time": task_time.strip()}
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
        nlu_result = self.parse_nlu(command)
        if nlu_result["action"] == "greet":
            self.state = "greeting"
            suggestion = self.suggest_task()
            return f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"
        elif nlu_result["action"] == "add":
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.tasks[timestamp] = nlu_result["desc"]
            return f"Yay! Added task: {nlu_result['desc']} at {timestamp}!"
        elif nlu_result["action"] == "schedule":
            try:
                schedule_time = datetime.strptime(nlu_result["time"], "%H:%M")
                schedule_time = schedule_time.replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day
                )
                if schedule_time < datetime.now():
                    schedule_time += timedelta(days=1)
                timestamp = schedule_time.strftime("%H:%M:%S")
                self.scheduled_tasks[timestamp] = {"desc": nlu_result["desc"], "recurring": nlu_result["recurring"]}
                return f"Woo-hoo! Scheduled {nlu_result['desc']} for {timestamp}!"
            except ValueError:
                return "Oops! Couldn’t parse time. Use ‘at HH:MM’ or similar."
        elif nlu_result["action"] == "complete":
            task_time = nlu_result["time"]
            all_tasks = {**self.tasks, **{k: v["desc"] for k, v in self.scheduled_tasks.items()}}
            if any(task_time in t for t in all_tasks):
                for t in list(self.tasks.keys()):
                    if task_time in t:
                        desc = self.tasks.pop(t)
                        self.completed_tasks[t] = desc
                        return f"Great job! Marked {t}: {desc} as complete!"
                for t in list(self.scheduled_tasks.keys()):
                    if task_time in t:
                        desc = self.scheduled_tasks.pop(t)["desc"]
                        self.completed_tasks[t] = desc
                        return f"Great job! Marked {t}: {desc} as complete!"
            elif task_time in self.completed_tasks:
                return f"Already completed {task_time}: {self.completed_tasks[task_time]}!"
            return "Task not found! Use a time like '11:15:00'."
        elif nlu_result["action"] == "review":
            if self.completed_tasks:
                return "Completed tasks:\n" + "\n".join(f"{t}: {d}" for t, d in self.completed_tasks.items())
            return "No tasks completed yet!"
        elif nlu_result["action"] == "list":
            all_tasks = {**self.tasks, **{k: v["desc"] for k, v in self.scheduled_tasks.items()}}
            if all_tasks or self.completed_tasks:
                return ("Your tasks:\n" + "\n".join(f"{t}: {d}" for t, d in all_tasks.items()) + 
                        "\nCompleted tasks:\n" + "\n".join(f"{t}: {d}" for t, d in self.completed_tasks.items()))
            return "No tasks yet—give me something to do!"
        elif nlu_result["action"] == "clear":
            self.tasks.clear()
            self.scheduled_tasks.clear()
            self.completed_tasks.clear()
            return "Tasks cleared! I’m all fresh now!"
        elif nlu_result["action"] == "exit":
            self.state = "exiting"
            return "Catch you later! Saving my notes..."
        elif nlu_result["action"] == "unknown":
            return nlu_result.get("message", f"Oops! I’m puzzled. Try natural commands like ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘complete task:HH:MM:SS’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’.")

    def suggest_task(self):
        current_hour = datetime.now().hour
        if 12 <= current_hour < 14:
            return "How about scheduling lunch around 12:30?"
        elif 17 <= current_hour < 19:
            return "Maybe schedule dinner prep for 17:30?"
        return "No suggestions right now—add your own task!"

    def visualize(self):
        self.screen.fill((0, 0, 0))
        if self.state == "greeting":
            pygame.draw.circle(self.screen, (0, 255, 0), (200, 150), 50)
        elif self.state == "exiting":
            pygame.draw.circle(self.screen, (255, 0, 0), (200, 150), 50)
        text_surface = self.font.render(self.input_buffer, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))
        pygame.display.flip()

    def check_scheduled_tasks(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        current_minute = datetime.now().strftime("%H:%M")
        for timestamp in list(self.scheduled_tasks.keys()):
            scheduled_dt = datetime.strptime(timestamp, "%H:%M:%S")
            current_dt = datetime.strptime(current_time, "%H:%M:%S")
            if (scheduled_dt <= current_dt and 
                current_minute not in self.last_notified.get(timestamp, []) and
                timestamp in self.scheduled_tasks):
                task_data = self.scheduled_tasks.get(timestamp)
                if task_data:
                    print(f"⏰ Alert! Time to {task_data['desc']} at {timestamp}!")
                    if self.alert_sound:
                        self.alert_sound.play()
                    elif self.beep_sound:
                        self.beep_sound.play()
                    else:
                        print("No sound available—check alert.wav or beep.wav.")
                    self.state = "greeting"
                    self.visualize()
                    time.sleep(1)
                    if task_data["recurring"]:
                        schedule_time = datetime.strptime(timestamp, "%H:%M:%S")
                        schedule_time = schedule_time.replace(
                            year=datetime.now().year,
                            month=datetime.now().month,
                            day=datetime.now().day + 1
                        )
                        new_timestamp = schedule_time.strftime("%H:%M:%S")
                        self.scheduled_tasks[new_timestamp] = task_data
                    else:
                        self.scheduled_tasks.pop(timestamp)
                    self.last_notified.setdefault(timestamp, []).append(current_minute)

    def run(self):
        running = True
        while running:
            self.check_scheduled_tasks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and self.input_buffer:
                        response = self.respond(self.input_buffer)
                        print(response)
                        self.visualize()
                        self.input_buffer = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    elif event.unicode.isprintable():
                        self.input_buffer += event.unicode
                    self.visualize()
            pygame.time.delay(1000)
        os.makedirs("data", exist_ok=True)
        with open("data/tasks.json", "w") as f:
            json.dump({"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks, "completed_tasks": self.completed_tasks}, f, indent=4)
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()