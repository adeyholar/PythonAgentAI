import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FONT_SIZE, TEXT_COLOR, BACKGROUND_COLOR, AGENT_COLOR_IDLE, AGENT_COLOR_GREETING, AGENT_COLOR_EXITING, AGENT_COLOR_ALERT

class UIManager:
    def __init__(self, max_response_lines):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.max_response_lines = max_response_lines
        self.response_display = []
        self.input_buffer = ""
        self.expanded = False

    def add_response(self, response):
        for line in response.split('\n'):
            self.response_display.append(line)
        if len(self.response_display) > self.max_response_lines:
            self.response_display = self.response_display[-self.max_response_lines:]

    def visualize(self, state, input_buffer):
        width, height = (1200, 900) if self.expanded else (SCREEN_WIDTH, SCREEN_HEIGHT)
        if self.screen.get_size() != (width, height):
            pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.screen.fill(BACKGROUND_COLOR)
        agent_color = AGENT_COLOR_IDLE
        if state == "greeting":
            agent_color = AGENT_COLOR_GREETING
        elif state == "exiting":
            agent_color = AGENT_COLOR_EXITING
        elif state == "alert":
            agent_color = AGENT_COLOR_ALERT
        pygame.draw.circle(self.screen, agent_color, (width // 2, height // 3), 70)
        y_offset = height // 2 + 20
        for line_text in reversed(self.response_display):
            text_surface = self.font.render(line_text, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(width // 2, y_offset))
            self.screen.blit(text_surface, text_rect.topleft)
            y_offset -= FONT_SIZE
        input_prompt = "You: " + input_buffer
        input_surface = self.font.render(input_prompt, True, TEXT_COLOR)
        self.screen.blit(input_surface, (10, height - FONT_SIZE - 10))
        pygame.display.flip()