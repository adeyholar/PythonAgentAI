import numpy as np
import pygame

class SimpleAgent:
    def __init__(self):
        self.state = "idle"
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Simple Agent")

    def respond(self, command):
        if "hello" in command.lower():
            self.state = "greeting"
            return "Hello! I’m your agent. How can I help?"
        elif "exit" in command.lower():
            self.state = "exiting"
            return "Goodbye!"
        else:
            return "I don’t understand. Try 'hello' or 'exit'."

    def visualize(self):
        self.screen.fill((0, 0, 0))  # Black background
        if self.state == "greeting":
            pygame.draw.circle(self.screen, (0, 255, 0), (200, 150), 50)  # Green circle
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

if __name__ == "__main__":
    agent = SimpleAgent()
    agent.run()