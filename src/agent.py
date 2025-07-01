import numpy as np
import pygame
import json
from datetime import datetime

class SimpleAgent:
    def __init__(self):
        self.state = "idle"
        self.memory = {}  # Simple in-memory storage
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Simple Agent")

    def respond(self, command):
        command = command.lower().strip()
        if "hello" in command:
            self.state = "greeting"
            response = "Hello! I’m your agent. How can I help?"
        elif "remember" in command and ":" in command:
            key, value = command.split(":", 1)
            self.memory[key.strip()] = value.strip()
            response = f"Remembered: {key} = {value}"
        elif "recall" in command and any(k in command for k in self.memory):
            for k in self.memory:
                if k in command:
                    response = f"Recalling: {k} = {self.memory[k]}"
                    break
            else:
                response = "Nothing to recall for that key."
        elif "exit" in command:
            self.state = "exiting"
            response = "Goodbye!"
        else:
            response = "I don’t understand. Try 'hello', 'remember key:value', 'recall key', or 'exit'."
        self.memory[datetime.now().strftime("%H:%M:%S")] = response
        return response

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
        pygame.quit()
        with open("data/memory.json", "w") as f:
            json.dump(self.memory, f, indent=4)

if __name__ == "__main__":
    agent = SimpleAgent()
    agent.run()