import numpy as np
import pygame
import json
from datetime import datetime, timedelta
import os
import time
import random

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
        pygame.mixer.init()  # Initialize mixer for sound

    def respond(self, command):
        command = command.lower().strip()
        if "hello" in command:
            self.state = "greeting"
            suggestion = self.suggest_task()
            return f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"
        elif "add task" in command and ":" in command:
            _, desc = command.split(":", 1)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.tasks[timestamp] = desc.strip()
            return f"Yay! Added task: {desc} at {timestamp}!"
        elif "schedule task" in command and ":" in command:
            parts = command.split(":", 1)[1].split(" at ")
            if len(parts) == 2:
                desc, time_str = parts
                try:
                    schedule_time = datetime.strptime(time_str.strip(), "%H:%M")
                    schedule_time = schedule_time.replace(
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day
                    )
                    if schedule_time < datetime.now():
                        schedule_time += timedelta(days=1)
                    timestamp = schedule_time.strftime("%H:%M:%S")
                    self.scheduled_tasks[timestamp] = {"desc": desc.strip(), "recurring": False}
                    return f"Woo-hoo! Scheduled {desc} for {timestamp}!"
                except ValueError:
                    return "Oops! Use format 'schedule task:desc at HH:MM' (e.g., 14:00)."
        elif "schedule recurring" in command and ":" in command:
            parts = command.split(":", 1)[1].split(" at ")
            if len(parts) == 2:
                desc, time_str = parts
                try:
                    schedule_time = datetime.strptime(time_str.strip(), "%H:%M")
                    schedule_time = schedule_time.replace(
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day
                    )
                    if schedule_time < datetime.now():
                        schedule_time += timedelta(days=1)
                    timestamp = schedule_time.strftime("%H:%M:%S")
                    self.scheduled_tasks[timestamp] = {"desc": desc.strip(), "recurring": True}
                    return f"Super! Scheduled recurring {desc} for {timestamp} daily!"
                except ValueError:
                    return "Oops! Use format 'schedule recurring:desc at HH:MM'."
        elif "complete task" in command and ":" in command:
            _, task_time = command.split(":", 1)
            task_time = task_time.strip()
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
        elif "review completed" in command:
            if self.completed_tasks:
                return "Completed tasks:\n" + "\n".join(f"{t}: {d}" for t, d in self.completed_tasks.items())
            return "No tasks completed yet!"
        elif "list tasks" in command:
            all_tasks = {**self.tasks, **{k: v["desc"] for k, v in self.scheduled_tasks.items()}}
            if all_tasks or self.completed_tasks:
                return ("Your tasks:\n" + "\n".join(f"{t}: {d}" for t, d in all_tasks.items()) + 
                        "\nCompleted tasks:\n" + "\n".join(f"{t}: {d}" for t, d in self.completed_tasks.items()))
            return "No tasks yet—give me something to do!"
        elif "clear tasks" in command:
            self.tasks.clear()
            self.scheduled_tasks.clear()
            self.completed_tasks.clear()
            return "Tasks cleared! I’m all fresh now!"
        elif "exit" in command:
            self.state = "exiting"
            return "Catch you later! Saving my notes..."
        else:
            return f"Oops! I’m puzzled. Try ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘complete task:HH:MM:SS’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’."

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
                    pygame.mixer.music.load("alert.wav")  # Requires an alert.wav file
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(100)
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