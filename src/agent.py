import numpy as np
import pygame
import json
from datetime import datetime
import os

class ChattyAgent:
    def __init__(self):
        self.state = "idle"
        self.tasks = {}  # Task list with timestamps
        self.personality = "cheerful"  # Can be "cheerful", "sarcastic", etc.
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Chatty Agent")

    def respond(self, command):
        command = command.lower().strip()
        if "hello" in command:
            self.state = "greeting"
            return f"Hey there! I’m your {self.personality} agent, ready to assist! What’s on your mind?"
        elif "add task" in command and ":" in command:
            task, desc = command.split(":", 1)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.tasks[timestamp] = desc.strip()
            return f"Yay! Added task: {desc} at {timestamp}!"
        elif "list tasks" in command:
            if self.tasks:
                return "Your tasks:\n" + "\n".join(f"{t}: {d}" for t, d in self.tasks.items())
            return "No tasks yet—give me something to do!"
        elif "clear tasks" in command:
            self.tasks.clear()
            return "Tasks cleared! I’m all fresh now!"
        elif "exit" in command:
            self.state = "exiting"
            return "Catch you later! Saving my notes..."
        else:
            return f"Hmm, I’m stumped! Try ‘hello’, ‘add task:desc’, ‘list tasks’, ‘clear tasks’, or ‘exit’."

    def visualize(self):
        self.screen.fill((0, 0, 0))  # Black background
        if self.state == "greeting":
            pygame.draw.circle(self.screen, (0, 255, 0), (200, 150), 50)  # Green circle
        elif self.state == "exiting":
            pygame.draw.circle(self.screen, (255, 0, 0), (200, 150), 50)  # Red circle
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.unicode:
                        response = self.respond(event.unicode)
                        print(response)
                        self.visualize()
            pygame.time.delay(100)
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        with open("data/tasks.json", "w") as f:
            json.dump(self.tasks, f, indent=4)
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()