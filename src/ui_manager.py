# ui_manager.py
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FONT_SIZE, TEXT_COLOR, BACKGROUND_COLOR, \
                   AGENT_COLOR_IDLE, AGENT_COLOR_GREETING, AGENT_COLOR_EXITING, AGENT_COLOR_ALERT, \
                   ALERT_SOUND_FILE, BEEP_SOUND_FILE # Import sound file paths

class UIManager:
    def __init__(self, max_response_lines):
        self.max_response_lines = max_response_lines
        self.response_display = []
        self._input_buffer = "" # Renamed to private to manage internally
        self.expanded = False
        self.screen = None  # Will be set by set_screen
        self.font = None    # Will be set by set_screen

        # Sound loading (moved here from ChattyAgent)
        # pygame.mixer.init() should be called ONCE in ChattyAgent init before UIManager is created
        self.alert_sound = self._load_sound(ALERT_SOUND_FILE)
        self.beep_sound = self._load_sound(BEEP_SOUND_FILE)
        if not self.alert_sound or not self.beep_sound:
            print("Warning: Sound files may not load correctly in UIManager. Ensure 'alert.wav' and 'beep.wav' exist.")

    def _load_sound(self, filename):
        try:
            return pygame.mixer.Sound(filename)
        except pygame.error as e:
            print(f"Warning: Could not load sound file '{filename}': {e}")
            return None

    def set_screen(self, screen): # Renamed initialize to set_screen
        """Sets the Pygame display surface and initializes font."""
        self.screen = screen
        # Font should only be initialized once, or re-initialized if font size changes
        # For simplicity, assuming font size is constant for now
        if self.font is None: # Only create font once
            self.font = pygame.font.Font(None, FONT_SIZE)

    def get_input_buffer(self):
        return self._input_buffer

    def add_to_input_buffer(self, char):
        self._input_buffer += char

    def remove_from_input_buffer(self):
        self._input_buffer = self._input_buffer[:-1]

    def clear_input_buffer(self):
        self._input_buffer = ""

    def add_response(self, response):
        for line in response.split('\n'):
            self.response_display.append(line)
        # Keep only the last max_response_lines
        if len(self.response_display) > self.max_response_lines:
            self.response_display = self.response_display[-self.max_response_lines:]

    def toggle_expanded(self):
        self.expanded = not self.expanded
        # UIManager only toggles the flag. ChattyAgent's run loop will
        # respond to this flag to change the actual Pygame window size.

    def visualize(self, state): # input_buffer is no longer passed as argument, use self._input_buffer
        if self.screen is None or self.font is None: # Check both screen and font
            print("UIManager: Screen or Font not initialized for visualization.")
            return

        # Always draw to the current screen size. The main loop is responsible for set_mode on resize.
        width, height = self.screen.get_size()

        self.screen.fill(BACKGROUND_COLOR)

        agent_color = AGENT_COLOR_IDLE
        if state == "greeting":
            agent_color = AGENT_COLOR_GREETING
        elif state == "exiting":
            agent_color = AGENT_COLOR_EXITING
        elif state == "alert":
            agent_color = AGENT_COLOR_ALERT
        pygame.draw.circle(self.screen, agent_color, (width // 2, height // 3), 70)

        # Display responses
        y_offset = height // 2 + 20
        # Ensure we don't go off screen for very long responses, drawing from bottom up
        # Only render lines that will fit on screen starting from y_offset
        current_y = y_offset
        for line_text in reversed(self.response_display):
            text_surface = self.font.render(line_text, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(width // 2, current_y))
            # Adjust topleft for proper alignment or use centery/midbottom
            text_rect.topleft = (width // 2 - text_surface.get_width() // 2, current_y - text_surface.get_height() // 2)

            # Only blit if it's within the visible area
            if text_rect.bottom > height // 2 and text_rect.top < height - FONT_SIZE * 2: # Simple bounds check
                self.screen.blit(text_surface, text_rect.topleft)
            current_y -= FONT_SIZE # Move up for next line

        # Display input prompt at the bottom
        input_prompt = "You: " + self._input_buffer # Use internal buffer
        input_surface = self.font.render(input_prompt, True, TEXT_COLOR)
        # Position at the bottom left, with a small padding
        self.screen.blit(input_surface, (10, height - FONT_SIZE - 10))
        
        pygame.display.flip()

    def play_alert_sound(self):
        if self.alert_sound:
            self.alert_sound.play()
        elif self.beep_sound: # Fallback to beep if alert sound isn't available
            self.beep_sound.play()
        else:
            print("No sound available for alert—check sound files.")