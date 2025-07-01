import pygame
import time
import threading
from datetime import datetime, timedelta
from task_manager import TaskManager
from nlu_parser import NLUParser
from external_services import OllamaClient, EmailClient
from ui_manager import UIManager
from config import CHECK_INTERVAL, BLOG_INTERVAL

class ChattyAgent:
    def __init__(self):
        self.task_manager = TaskManager()
        self.nlu = NLUParser()
        self.ollama_client = OllamaClient()
        self.email_client = EmailClient()
        self.ui = UIManager(15)
        self.state = "idle"
        self.personality = "cheerful"
        self.alert_sound = self._load_sound("alert.wav")
        self.beep_sound = self._load_sound("beep.wav")
        self.last_check_time = time.time()
        self.task_manager.load_state("agent_data/tasks.json")

    def _load_sound(self, filename):
        try:
            return pygame.mixer.Sound(filename)
        except pygame.error:
            print(f"Warning: Could not load sound file '{filename}'.")
            return None

    def _schedule_blog_generation(self):
        while True:
            now = datetime.now()
            next_interval = now + timedelta(seconds=BLOG_INTERVAL)
            wait_time = (next_interval - now).total_seconds()
            time.sleep(wait_time)
            blog_content = self.ollama_client.generate_blog()
            subject = f"Blog Post - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.email_client.send_email(subject, blog_content)
            self.ui.add_response(f"Blog generated and emailed at {datetime.now().strftime('%H:%M')}")

    def respond(self, command):
        nlu_result = self.nlu.parse(command)

        response_text = "..."  # Default response

        if nlu_result["action"] == "greet":
            self.state = "greeting"
            suggestion = self.suggest_task()
            response_text = f"Hey there! I’m your {self.personality} agent, ready to assist! {suggestion}"

        elif nlu_result["action"] == "add":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.task_manager.add_task(nlu_result["desc"], timestamp)
            response_text = f"Yay! Added task: {nlu_result['desc']} at {timestamp}!"

        elif nlu_result["action"] == "schedule":
            try:
                today = datetime.now().date()
                scheduled_dt_candidate = datetime.strptime(nlu_result["time"], "%H:%M").time()
                scheduled_datetime = datetime.combine(today, scheduled_dt_candidate)
                if scheduled_datetime < datetime.now():
                    scheduled_datetime += timedelta(days=1)
                self.task_manager.schedule_task(nlu_result["desc"], scheduled_datetime, nlu_result["recurring"], nlu_result["priority"])
                response_text = f"Woo-hoo! Scheduled '{nlu_result['desc']}' (Priority: {nlu_result['priority']}) for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!"
            except ValueError:
                response_text = "Oops! Couldn’t process the scheduled time."

        elif nlu_result["action"] == "set_priority":
            desc, timestamp = self.task_manager.set_priority(nlu_result["task_time"], nlu_result["priority"])
            response_text = f"Updated priority for '{desc}' at {timestamp} to {nlu_result['priority']}" if desc else f"No scheduled task found with time '{nlu_result['task_time']}'."

        elif nlu_result["action"] == "feedback":
            response_text = nlu_result.get("response_text", "Feedback processed.")  # Fallback if response_text is missing

        elif nlu_result["action"] == "generate_blog":
            blog_content = self.ollama_client.generate_blog()
            subject = f"Blog Post - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.email_client.send_email(subject, blog_content)
            response_text = f"Generated and emailed blog post: {subject}\n{blog_content[:100]}..."

        elif nlu_result["action"] == "complete":
            desc, timestamp = self.task_manager.complete_task(nlu_result["identifier"])
            response_text = f"Great job! Marked '{desc}' ({timestamp}) as complete!" if desc else f"Task '{nlu_result['identifier']}' not found."

        elif nlu_result["action"] == "review":
            if self.task_manager.completed_tasks:
                response_text = "Completed tasks:\n" + "\n".join(f"- {t}: {d}" for t, d in self.task_manager.completed_tasks.items())
            else:
                response_text = "No tasks completed yet!"

        elif nlu_result["action"] == "list":
            all_active_tasks = {**self.task_manager.tasks, **{k: v["desc"] for k, v in self.task_manager.scheduled_tasks.items()}}
            active_list = [f"- {t}: {v['desc']} (Priority: {v.get('priority', 1)})" for t, v in self.task_manager.scheduled_tasks.items()] + \
                          [f"- {t}: {d}" for t, d in self.task_manager.tasks.items()] if all_active_tasks else []
            completed_list = [f"- {t}: {d}" for t, d in sorted(self.task_manager.completed_tasks.items())] if self.task_manager.completed_tasks else []
            response_text = "Your tasks:\n" + "\n".join(sorted(active_list)) if active_list else ""
            if completed_list:
                response_text += "\nCompleted tasks:\n" + "\n".join(completed_list)
            if not active_list and not completed_list:
                response_text = "No tasks yet—give me something to do!"

        elif nlu_result["action"] == "clear":
            self.task_manager.clear_tasks()
            response_text = "All tasks cleared! I’m all fresh now!"

        elif nlu_result["action"] == "exit":
            self.state = "exiting"
            response_text = "Catch you later! Saving my notes..."

        elif nlu_result["action"] == "unknown":
            response_text = nlu_result.get("message", f"Oops! I’m puzzled. Try natural commands like ‘hello’, ‘add task:desc’, ‘schedule task:desc at HH:MM’, ‘schedule recurring:desc at HH:MM’, ‘set priority:TIME to PRIORITY’, ‘feedback:SUGGESTION on LIKE/DISLIKE’, ‘generate blog’, ‘complete task:TIME_OR_DESC’, ‘review completed’, ‘list tasks’, ‘clear tasks’, or ‘exit’.")

        self.ui.add_response(response_text)
        return response_text

    def suggest_task(self):
        current_time = datetime.now()
        suggestions = []
        for timestamp, task_data in self.task_manager.scheduled_tasks.items():
            scheduled_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            time_diff = (scheduled_dt - current_time).total_seconds() / 60
            if 0 < time_diff <= 120:
                urgency = max(1, 120 - time_diff)
                priority_score = urgency * task_data["priority"]
                suggestions.append((priority_score, f"Schedule {task_data['desc']} at {scheduled_dt.strftime('%H:%M')} (in {int(time_diff)} minutes, Priority: {task_data['priority']})"))
        if suggestions:
            suggestions.sort(reverse=True)
            return suggestions[0][1]

        if self.task_manager.task_history:
            adjusted_history = {}
            for task, frequency in self.task_manager.task_history.items():
                feedback = self.task_manager.feedback_history.get(task.lower(), 0)
                adjusted_score = frequency * (1 + feedback)
                adjusted_history[task] = adjusted_score
            if adjusted_history:
                most_frequent_task = max(adjusted_history.items(), key=lambda x: x[1])[0]
                next_hour = (current_time.hour + 1) % 24
                suggested_time = current_time.replace(hour=next_hour, minute=0, second=0)
                if suggested_time < current_time:
                    suggested_time += timedelta(days=1)
                return f"Based on your habits, how about scheduling {most_frequent_task} at {suggested_time.strftime('%H:%M')}? (Provide feedback with 'feedback:{most_frequent_task} on like/good' or 'dislike/bad')"
        current_hour = current_time.hour
        if 12 <= current_hour < 14:
            return "Perhaps it's time to schedule lunch around 12:30?"
        elif 17 <= current_hour < 19:
            return "Maybe schedule dinner prep for 17:30?"
        elif 21 <= current_hour < 23:
            return "Don't forget to schedule your bedtime routine around 22:00?"
        return "No specific suggestions right now—add your own task!"

    def check_scheduled_tasks(self):
        current_datetime = datetime.now()
        for timestamp_key in list(self.task_manager.scheduled_tasks.keys()):
            task_data = self.task_manager.scheduled_tasks.get(timestamp_key)
            if not task_data:
                continue
            try:
                scheduled_dt = datetime.strptime(timestamp_key, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"Warning: Invalid timestamp format for '{timestamp_key}'. Removing task.")
                del self.task_manager.scheduled_tasks[timestamp_key]
                continue
            current_day = current_datetime.strftime("%Y-%m-%d")
            last_notified_day = self.task_manager.last_notified.get(timestamp_key, {}).get("day", "")
            if (current_datetime >= scheduled_dt and 
                current_day not in self.task_manager.last_notified.get(timestamp_key, {}).get("days", [])):
                try:
                    alert_message = f"⏰ Alert! Time to {task_data['desc']} at {scheduled_dt.strftime('%Y-%m-%d %H:%M')}"
                    self.ui.add_response(alert_message)
                    print(alert_message)
                    self.state = "alert"
                    self.ui.visualize(self.state, self.input_buffer)
                    if self.alert_sound:
                        self.alert_sound.play()
                    elif self.beep_sound:
                        self.beep_sound.play()
                    else:
                        print("No sound available—check sound files.")
                    if timestamp_key not in self.task_manager.last_notified:
                        self.task_manager.last_notified[timestamp_key] = {"days": []}
                    self.task_manager.last_notified[timestamp_key]["days"].append(current_day)
                    if task_data["recurring"]:
                        new_scheduled_dt = scheduled_dt + timedelta(days=1)
                        new_timestamp_key = new_scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")
                        self.task_manager.scheduled_tasks[new_timestamp_key] = task_data
                        print(f"Rescheduled recurring task '{task_data['desc']}' for {new_scheduled_dt.strftime('%Y-%m-%d %H:%M')}.")
                    else:
                        del self.task_manager.scheduled_tasks[timestamp_key]
                        print(f"One-time task '{task_data['desc']}' completed and removed.")
                except Exception as e:
                    print(f"Error during alert processing for {timestamp_key} on line ~225: {e}")
                finally:
                    time.sleep(0.5)
                    self.state = "idle"
                    self.ui.visualize(self.state, self.input_buffer)

    def run(self):
        import threading
        blog_thread = threading.Thread(target=self._schedule_blog_generation, daemon=True)
        blog_thread.start()
        running = True
        last_check_time = time.time()
        while running:
            current_loop_time = time.time()
            if current_loop_time - last_check_time >= CHECK_INTERVAL:
                self.check_scheduled_tasks()
                last_check_time = current_loop_time
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.ui.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.ui.visualize(self.state, self.input_buffer)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.input_buffer:
                            print(f"Processing input: '{self.input_buffer}'")
                            response = self.respond(self.input_buffer)
                            print(f"Agent says: {response}")
                            self.input_buffer = ""
                        self.ui.visualize(self.state, self.input_buffer)
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_buffer = self.input_buffer[:-1]
                    elif event.key == pygame.K_e:
                        self.ui.expanded = not self.ui.expanded
                        self.ui.visualize(self.state, self.input_buffer)
                    elif event.unicode.isprintable():
                        self.input_buffer += event.unicode
                    self.ui.visualize(self.state, self.input_buffer)
            pygame.time.delay(50)
        self.task_manager.save_state("agent_data/tasks.json")
        pygame.quit()

if __name__ == "__main__":
    agent = ChattyAgent()
    agent.run()