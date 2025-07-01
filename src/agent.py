import numpy as np
import pygame
import json
from datetime import datetime, timedelta
import os
import time

class ChattyAgent:
    def __init__(self):
        self.state = "idle"
        self.tasks = {}
        self.scheduled_tasks = {}
        self.personality = "cheerful"
        self.input_buffer = ""
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Chatty Agent")
        self.font = pygame.font.Font(None, 36)

    def respond(self, command):
        command = command.lower().strip()
        if "hello" in command:
            self.state = "greeting"
            return f"Hey there! I’m your {self.personality} agent, ready to assist! What’s on your mind?"
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
                    self.scheduled_tasks[timestamp] = desc.strip()
                    return f"Woo-hoo! Scheduled {desc} for {timestamp}!"
                except ValueError:
                    return "Oops! Use format 'schedule task:desc at HH:MM' (e.g., 14:00)."
        elif "list tasks" in command:
            all_tasks = {**self.tasks, **self.scheduled_tasks}
            if all_tasks:
                return "Your tasks:\n" + "\n".join(f"{t}: {d}" for t, d in all_tasks.items())
            return "No tasks yet—give me something to do!"
        elif "clear tasks" in command:
            self.tasks.clear()
            self.scheduled_tasks.clear()
            return "Tasks cleared! I’m all fresh now!"
        elif "exit" in command:
            self.state = "exiting"
            return "Catch you later! Saving my notes..."
        else:
            return f"Oops! I’m puzzled. Try ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘list tasks’, ‘clear tasks’, or ‘exit’."

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
        for timestamp in list(self.scheduled_tasks.keys()):
            if timestamp <= current_time:
                task = self.scheduled_tasks.pop(timestamp)
                print(f"⏰ Alert! Time to {task} at {timestamp}!")
                self.visualize()  # Flash the screen to notify
                time.sleep(1)  # Brief pause

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
            pygame.time.delay(1000)  # Increase delay to reduce CPU load
        os.makedirs("data", exist_ok=True)
        with open("data/tasks.json", "w") as f:
            json.dump({"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks}, f, indent=4)
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()