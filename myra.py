import asyncio
import datetime
import getpass
import json
import os
import random
import re
import tempfile
import subprocess
import webbrowser
from urllib.parse import quote_plus

import requests
import edge_tts
import sounddevice as sd
import speech_recognition as sr
from playsound import playsound
import pyautogui


# ==========================================
# MYRA AI - HYBRID WINDOWS ASSISTANT
# ==========================================

APP_NAME = "Myra AI"

VOICE = "en-IN-NeerjaNeural"

AI_MODEL = "gpt-4o-mini"
AI_URL = "https://api.openai.com/v1/chat/completions"

SAMPLE_RATE = 16000
CHANNELS = 1

# Set True to require "Hey Myra" before commands.
REQUIRE_WAKE_WORD = False

recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8

# ==========================================
# CONFIGURATION AND API KEY
# ==========================================

APP_FOLDER = os.path.join(
    os.getenv("APPDATA", os.path.expanduser("~")),
    "MyraAI"
)

CONFIG_FILE = os.path.join(APP_FOLDER, "config.json")

os.makedirs(APP_FOLDER, exist_ok=True)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            pass

    return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)


def get_api_key():
    config = load_config()

    api_key = config.get("api_key", "").strip()

    if api_key:
        return api_key

    print("\nWelcome to Myra AI!")
    print("Enter your own OpenAI API key.")
    print("Your key will be stored locally on this computer.")
    print("Never share your API key with anyone.\n")

    api_key = getpass.getpass("Enter OpenAI API key: ").strip()

    if not api_key:
        print("No API key entered. AI conversations will be unavailable.")
        return None

    config["api_key"] = api_key
    save_config(config)

    print("\nAPI key saved successfully!")

    return api_key


API_KEY = get_api_key()


# ==========================================
# CHAT HISTORY
# ==========================================

chat_history = [
    {
        "role": "system",
        "content": (
            "You are Myra, a friendly female personal AI assistant. "
            "Answer helpfully and accurately. "
            "Use simple English, Hindi or Hinglish depending on the user. "
            "Explain programming step by step for beginners. "
            "Keep spoken answers concise. "
            "You are running on a Windows computer."
        )
    }
]


# ==========================================
# TEXT TO SPEECH
# ==========================================

async def speak(text):

    print("\nMyra:", text)

    audio_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        ) as file:
            audio_path = file.name

        tts = edge_tts.Communicate(
            text=text,
            voice=VOICE
        )

        await tts.save(audio_path)

        await asyncio.to_thread(
            playsound,
            audio_path
        )

    except Exception as error:
        print("Voice error:", repr(error))

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ==========================================
# SPEECH RECOGNITION
# ==========================================

def listen(seconds=5):

    try:
        print("\nListening...")

        recording = sd.rec(
            int(seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16"
        )

        sd.wait()

        audio = sr.AudioData(
            recording.reshape(-1).tobytes(),
            SAMPLE_RATE,
            2
        )

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        ).lower().strip()

        print("You:", text)

        return text

    except sr.UnknownValueError:
        return None

    except sr.RequestError as error:
        print("Internet speech recognition error:", error)
        return None

    except Exception as error:
        print("Microphone error:", repr(error))
        return None


# ==========================================
# WAKE WORD
# ==========================================

def clean_text(text):

    text = text.lower().strip()

    replacements = {
        "hey myra": "myra",
        "hi myra": "myra",
        "hello myra": "myra",
        "hey maria": "myra",
        "hey mira": "myra",
        "hamara": "myra",
        "amaira": "myra",
        "maurya": "myra",
        "mayra": "myra",
        "my ra": "myra"
    }

    for wrong, correct in replacements.items():
        text = re.sub(
            r"\b" + re.escape(wrong) + r"\b",
            correct,
            text
        )

    return text


def remove_wake_word(text):

    text = clean_text(text)

    match = re.search(r"\bmyra\b", text)

    if match:
        text = text[match.end():]

    return text.strip(" ,.!?:;-")


def is_stop_command(text):

    command = remove_wake_word(text)

    return command in {
        "stop",
        "stop myra",
        "exit",
        "quit",
        "goodbye",
        "shutdown",
        "shut down",
        "stop listening"
    }


# ==========================================
# WEBSITE CONTROL
# ==========================================

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "github": "https://github.com",
    "spotify": "https://open.spotify.com",
    "youtube music": "https://music.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.in"
}


def open_website(name):

    url = WEBSITES.get(name)

    if url:
        webbrowser.open(url)
        return f"Opening {name}."

    # Open other website names using Google search.
    webbrowser.open(
        "https://www.google.com/search?q=" + quote_plus(name)
    )

    return f"Searching for {name}."


def close_website():

    try:
        pyautogui.hotkey("ctrl", "w")

        return "Closing the active browser tab."

    except Exception:
        return "I could not close the browser tab."


# ==========================================
# MUSIC CONTROL
# ==========================================

def play_music(song):

    if not song:
        webbrowser.open("https://music.youtube.com")
        return "Opening YouTube Music."

    search_url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(song)
    )

    webbrowser.open(search_url)

    return f"Searching YouTube for {song}."


# ==========================================
# APPLICATION CONTROL
# ==========================================

def open_application(app):

    applications = {
        "calculator": "calc.exe",
        "notepad": "notepad.exe",
        "paint": "mspaint.exe",
        "command prompt": "cmd.exe"
    }

    executable = applications.get(app)

    if executable:
        try:
            subprocess.Popen([executable])
            return f"Opening {app}."

        except Exception:
            return f"Sorry, I could not open {app}."

    if app == "chrome":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "chrome"])
            return "Opening Google Chrome."

        except Exception:
            return "I could not open Chrome."

    return None


# ==========================================
# QUICK COMMANDS
# ==========================================

def quick_answer(question):

    q = question.lower().strip()

    # Stop
    if is_stop_command(q):
        return "__STOP__"

    # Close browser tab
    if (
        q in {"close website", "close tab", "close browser tab"}
        or q.startswith("close youtube")
        or q.startswith("close google")
        or q.startswith("close website")
    ):
        return close_website()

    # Open websites
    if q.startswith("open "):
     website = q.replace("open ", "", 1).strip()

    if website.startswith("the "):
        website = website[4:]

    if website in WEBSITES:
        return open_website(website)

    return open_website(website)
    # Open another website
    if q.startswith("open website "):
        name = q.replace("open website ", "", 1).strip()
        return open_website(name)

    # Music commands
    if q in {
        "play music",
        "play some music",
        "open music"
    }:
        return play_music("")

    music_match = re.match(
        r"^(?:play|search for|find)\s+(.+)$",
        q
    )

    if music_match:
        song = music_match.group(1).strip()

        if song.startswith("music "):
            song = song[6:].strip()

        return play_music(song)

    # Open applications
    for app in [
        "calculator",
        "notepad",
        "paint",
        "command prompt",
        "chrome"
    ]:

        if q in {
            "open " + app,
            "open the " + app
        }:
            return open_application(app)

    # Time
    if (
        q == "time"
        or "what time" in q
        or "current time" in q
    ):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."

    # Date
    if (
        q == "date"
        or "what is the date" in q
        or "today date" in q
    ):
        today = datetime.datetime.now().strftime(
            "%A, %d %B %Y"
        )

        return f"Today is {today}."

    # Jokes
    if "joke" in q:

        return random.choice([
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why did the computer go to the doctor? It caught a virus!",
            "Why was the computer cold? It left its Windows open!"
        ])

    # Myra identity
    if "your name" in q or "who are you" in q:
        return "I am Myra, your personal AI assistant."

    if "who made you" in q or "who created you" in q:
        return "I am being developed using Python and AI technology."

    return None


# ==========================================
# CLOUD AI
# ==========================================

def ask_ai(question):

    if not API_KEY:
        return "Please configure your OpenAI API key to use AI conversations."

    chat_history.append({
        "role": "user",
        "content": question
    })

    try:

        response = requests.post(
            AI_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": chat_history,
                "temperature": 0.7
            },
            timeout=60
        )

        response.raise_for_status()

        answer = (
            response.json()["choices"][0]
            ["message"]["content"]
            .strip()
        )

        chat_history.append({
            "role": "assistant",
            "content": answer
        })

        # Keep conversation history limited.
        if len(chat_history) > 13:

            chat_history[:] = (
                [chat_history[0]] + chat_history[-12:]
            )

        return answer

    except requests.exceptions.ConnectionError:
        return "I cannot connect to the AI service. Please check your internet."

    except requests.exceptions.Timeout:
        return "The AI response took too long. Please try again."

    except requests.exceptions.HTTPError as error:

        print("API error:", error)

        return (
            "There is a problem with your API key, "
            "account access or API billing."
        )

    except Exception as error:

        print("AI error:", repr(error))

        return "Sorry, I could not get an AI response."


# ==========================================
# MAIN PROGRAM
# ==========================================

async def main():

    print("=" * 45)
    print("          MYRA AI ASSISTANT")
    print("=" * 45)

    print("\nFeatures:")
    print("- Voice assistant")
    print("- AI conversations")
    print("- Website control")
    print("- Music search")
    print("- Application control")
    print("- Time and date")

    print('\nSay "Hey Myra" followed by a command.')
    print('Say "Stop" to close Myra.')

    await speak(
        "Hello! I am Myra. "
        "I am ready to help you."
    )

    while True:

        try:

            heard = listen(seconds=5)

            if not heard:
                continue

            # Stop can work without wake word.
            if is_stop_command(heard):

                await speak(
                    "Okay, stopping now. Goodbye!"
                )

                break

            cleaned = clean_text(heard)

            # Require wake word.
            if REQUIRE_WAKE_WORD:

                if not re.search(r"\bmyra\b", cleaned):
                    continue

            question = remove_wake_word(cleaned)

            # If only Hey Myra was spoken.
            if not question:

                await speak("Yes, how can I help?")

                next_text = listen(seconds=8)

                if not next_text:
                    continue

                if is_stop_command(next_text):

                    await speak(
                        "Okay, stopping now. Goodbye!"
                    )

                    break

                question = remove_wake_word(next_text)

            if not question:
                continue

            # Quick local commands first.
            answer = quick_answer(question)

            # AI for other questions.
            if answer is None:

                print("\nThinking...")

                answer = await asyncio.to_thread(
                    ask_ai,
                    question
                )

            if answer == "__STOP__":

                await speak(
                    "Okay, stopping now. Goodbye!"
                )

                break

            await speak(answer)

        except KeyboardInterrupt:

            print("\nMyra stopped.")
            break

        except Exception as error:

            print("Something went wrong:", repr(error))


# ==========================================
# START MYRA
# ==========================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nMyra stopped.")