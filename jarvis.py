import speech_recognition as sr
import webbrowser
import pyttsx3
import musicLibrary
import threading # It will help us to work on a multitask plateform.
import datetime
import wikipedia
import tkinter as tk
from tkinter import messagebox
from openai import OpenAI
import os
import json
import pyaudio
import requests  # For COVID data
import cv2
from PIL import Image, ImageTk
import random
import subprocess
import pygetwindow as gw
import time
import re
import winsound
import asyncio
import edge_tts
import pygame
import uuid  # For unique filenames
from edge_tts import Communicate
import tempfile
import pywhatkit
from dotenv import load_dotenv
from bs4 import BeautifulSoup # For Top News Headlines 

voice_gender = "female"
VOICE_MALE = "en-IN-PrabhatNeural"
VOICE_FEMALE = "en-IN-NeerjaNeural"

recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Speed up voice output (optional)
engine.setProperty('rate', 180)

NOTES_FILE = "jarvis_notes.txt"
QNA_FILE = "ques_ans.json"


state = {
    "angle": 0,
    "blink": False,
    "called": False,
    "speaking": False
}

# Load Q&A from JSON
def load_ques_ans():
    try:
        with open(QNA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading Q&A: {e}")
        return {}

ques_ans= load_ques_ans()


def speak(text):
    state["speaking"] = True
    engine.say(text)
    engine.runAndWait()
    state["speaking"] = False


# Initialize pygame mixer once globally
pygame.mixer.init()

VOICE = "en-IN-NeerjaNeural"  # Female realistic voice
RATE = "+0%"  # Normal speed

async def edge_speak_async(text, voice):
    communicate = Communicate(text=text, voice=voice, rate=RATE)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    await communicate.save(filename)

    # Wait until file exists
    while not os.path.exists(filename):
        await asyncio.sleep(0.1)

    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # Wait until playback finishes
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        # Unload the music after playback
        pygame.mixer.music.unload()

    except Exception as e:
        print(f"[ERROR playing sound]: {e}")

    finally:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as cleanup_error:
            print(f"[WARNING during cleanup]: {cleanup_error}")

def speak(text):
    global voice_gender
    voice = VOICE_MALE if voice_gender == "male" else VOICE_FEMALE
    asyncio.run(edge_speak_async(text, voice))


# Load variables from .env file
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def aiProcess(command):
    try:
        import os
        import requests
        from urllib.parse import quote

        api_key = os.getenv("SERPAPI_KEY")
        query = quote(command)

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key
        }

        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()

        # 1. Direct answer box (like calculator, weather, famous people)
        if "answer_box" in data:
            ab = data["answer_box"]
            if "answer" in ab:
                return ab["answer"]
            elif "snippet" in ab:
                return ab["snippet"]
            elif "definition" in ab:
                return ab["definition"]
            elif "content" in ab:
                return ab["content"]

        # 2. Knowledge Graph (for people like MS Dhoni)
        if "knowledge_graph" in data:
            kg = data["knowledge_graph"]
            if "description" in kg:
                return f"{kg.get('title', '')} is {kg['description']}."
            elif "title" in kg:
                return f"{kg['title']}"

        # 3. Fallback: use top search result snippet
        if "organic_results" in data and len(data["organic_results"]) > 0:
            return data["organic_results"][0].get("snippet", "No snippet found.")

        return "Sorry, I couldn't find an answer."
    
    except Exception as e:
        print(f"[ERROR - Google API]: {e}")
        return "Something went wrong while searching Google."

def get_latest_headlines():
    try:
        base_url = "https://timesofindia.indiatimes.com"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        headlines = []
        count = 0

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            link = a["href"]

            if (
                title and len(title) > 30
                and "/videos" not in link.lower()
                and "/photos" not in link.lower()
                and "/city" not in link.lower()
            ):
                full_url = link if link.startswith("http") else base_url + link
                summary = get_article_summary(full_url)
                headlines.append((title, summary))
                count += 1

            if count >= 5:
                break

        if not headlines:
            return "Sorry, no headlines found."

        result = "Here are the top headlines from India:\n"
        for i, (title, summary) in enumerate(headlines):
            result += f"\n{i+1}. {title}\n   {summary.strip()}\n"

        return result

    except Exception as e:
        return f"Error fetching headlines: {e}"


def get_article_summary(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")

        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 40:
                return text
        return "No summary available."
    except Exception:
        return "Summary not available."       


def save_note(note):
    with open(NOTES_FILE, "a") as f:
        f.write(note + "\n")
    return "Note saved."

def read_notes():
    if not os.path.exists(NOTES_FILE):
        return "No notes found."
    with open(NOTES_FILE, "r") as f:
        return f.read().strip()

def capture_photo():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        filename = "captured_photo.jpg"
        cv2.imwrite(filename, frame)
        speak("Photo taken successfully.")
        update_photo_preview()
    else:
        speak("Failed to take photo.")
    cap.release()

def show_saved_photo():
    if os.path.exists("captured_photo.jpg"):
        os.startfile("captured_photo.jpg")
    else:
        speak("No photo found.")

def update_photo_preview():
    if os.path.exists("captured_photo.jpg"):
        img = Image.open("captured_photo.jpg")
        img = img.resize((200, 150))
        photo = ImageTk.PhotoImage(img)
        photo_label.config(image=photo)
        photo_label.image =photo


def get_covid_data(country="India"):
    url = f"https://disease.sh/v3/covid-19/countries/{country}"
    try:
        response = requests.get(url)
        data = response.json()
        report = (
            f"COVID-19 stats for {data['country']} - "
            f"Confirmed: {data['cases']}, "
            f"Active: {data['active']}, "
            f"Deaths: {data['deaths']}, "
            f"Recovered: {data['recovered']}."
        )
        return report
    except Exception:
        return "Sorry, I couldn't fetch the latest data right now." 


def parse_timer_command(command):
    match = re.search(r"set a timer for (\d+)\s*(second|seconds|minute|minutes|hour|hours)", command)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        seconds = value
        if "minute" in unit:
            seconds *= 60
        elif "hour" in unit:
            seconds *= 3600
        return seconds
    return None

def start_timer(seconds):
    def run_timer():
        speak(f"Timer set for {seconds // 60 if seconds >= 60 else seconds} "
            f"{'minutes' if seconds >= 60 else 'seconds'}")
        time.sleep(seconds)
        speak("Time's up!")
        winsound.Beep(1000, 5000)  # 5-second beep at 1000 Hz

    threading.Thread(target=run_timer, daemon=True).start()

            



def processCommand(c):
    c = c.lower()
    if "open google" in c:
        webbrowser.open("https://google.com")
        speak('Opening google')
    elif "close google" in c:
        for window in gw.getWindowsWithTitle("Google"):
           window.close()
           speak("closing google")

    elif "open whatsapp" in c:
       webbrowser.open("https://www.whatsapp.com")
       speak('Opening whatsapp')
    elif "close whatsapp" in c:
        for window in gw.getWindowsWithTitle("whatsapp"):
           window.close()
           speak("closing whatsapp")

    elif "set a timer for" in c:
        seconds = parse_timer_command(c)
        if seconds:
            start_timer(seconds)
        else:
            speak("Sorry, I couldn't understand the timer duration.")

    elif "open spotify" in c:
       webbrowser.open("https://spotify.com")
       speak('Opening spotify')
    elif "close spotify" in c:
        for window in gw.getWindowsWithTitle("spotify"):
           window.close()
           speak("closing spotify")
         
    elif "open instagram" in c:
        webbrowser.open("https://www.instagram.com")
        speak('Opening instagram')
    elif "close instagram" in c:
        for window in gw.getWindowsWithTitle("instagram"):
           window.close()
           speak("closing instagram")

    elif "open linkedin" in c:
        webbrowser.open("https://www.linkedin.com")
        speak('Opening linkedin')
    elif "close linkedin" in c:
        for window in gw.getWindowsWithTitle("linkedin"):
           window.close()
           speak("closing linkedin")

    elif "open youtube" in c:
        webbrowser.open("https://youtube.com")
        speak('Opening youtube')
    elif "close youtube" in c:
        for window in gw.getWindowsWithTitle("youtube"):
           window.close()
           speak("closing youtube")

    elif "open calculator" in c:
        subprocess.Popen("calc.exe")
        speak("Opening Calculator")
    elif "close calculator" in c:
        for window in gw.getWindowsWithTitle('Calculator'):
          window.close()
          speak("Closing Calculator")

    elif "open amazon" in c:
        webbrowser.open("https://www.amazon.in")
        speak('Opening amazon')
    elif "close amazon" in c:
        for window in gw.getWindowsWithTitle("amazon"):
           window.close()
           speak("closing amazon")

    elif "open lpu website" in c:
        webbrowser.open("https://www.lpu.in")
    elif"close lpu website" in c:
        for window in gw.getwindowswithTitle("lpu website"):
            window.close()
            speak("closing lpu website")

    elif "open digilocker" in c:
        webbrowser.open("https://www.digilocker.gov.in")
        speak('Opening digilocker')
    elif "close digilocker" in c:
        for window in gw.getWindowsWithTitle("digilocker"):
           window.close()
           speak("closing digilocker")

    elif "open news" in c:
        webbrowser.open("https://timesofindia.indiatimes.com")

    elif "open lpu" in c:
        webbrowser.open("https://maps.app.goo.gl/WNjSeWF69DH5gdSV7?g_st=aw")

    elif "open zoom" in c:
        webbrowser.open("https://www.zoom.com")
        speak('Opening zoom')
    elif "close zoom" in c:
        for window in gw.getWindowsWithTitle("zoom"):
           window.close()
           speak("closing zoom")

    elif "open my class" in c:
        webbrowser.open("https://sms.lpu.in/kd8ccLo1n")
    elif"close my class" in c:
        for window in gw.windowswithTitle("my class"):
            windows.close()
            speak("closing my class")

    elif "open chat gpt" in c:
        webbrowser.open("https://www.chatgpt.com")
        speak('Opening chatgpt')
    elif "close chat gpt" in c:
        for window in gw.getWindowsWithTitle("chatgpt"):
           window.close()
           speak("closing chatgpt")

    elif c.startswith("play"):
        song = c.replace("play", "").strip()
        speak(f"Playing {song} on YouTube")
        pywhatkit.playonyt(song)
    
    elif "time" in c: #  Tells current time – say “What’s the time?”
        now = datetime.datetime.now().strftime("%H:%M:%S")
        speak(f"The time is {now}")

    elif "date" in c:  #  Tells today’s date – say “Tell me the date”
        today = datetime.datetime.now().strftime("%A, %d %B %Y")
        speak(f"Today is {today}")

    elif "search wikipedia for" in c:  #  Wikipedia search – say “Search Wikipedia for [topic]” 
        topic = c.replace("search wikipedia for", "").strip()
        try:
            summary = wikipedia.summary(topic, sentences=2)
            speak(summary)
        except Exception:
            speak("Sorry, I couldn't find anything on Wikipedia.")

    elif "remind me to" in c or "note" in c:
        note = c.replace("remind me to", "").replace("note", "").strip()
        speak(save_note(note))

    elif "show notes" in c or "read notes" in c:
        speak(read_notes())

    elif "covid" in c:
        if "india" in c:
            report = get_covid_data("India")
        else:
            speak("Please tell me the country name.")
            with sr.Microphone() as source:
                audio = recognizer.listen(source)
                country = recognizer.recognize_google(audio)
                report = get_covid_data(country)
        speak(report)
        

    else:
        # Check for manual Q&A
        question = c.strip().lower()
        if question in ques_ans:
            speak(ques_ans[question])
        else:
            output = aiProcess(c)
            speak(output)
    

listening_mode = False   # Start inactive

def listen_and_process():
    global listening_mode
    try:
        with sr.Microphone() as source:
            if not listening_mode:
                print("Listening for wake word...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=2)
                word = recognizer.recognize_google(audio).lower()
                print(f"Detected: {word}")
                if "jarvis" in word:
                    listening_mode = True
                    speak("Yes! AMAN, how may I help you?")
                   
            else:
                print("Listening for command...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = recognizer.recognize_google(audio)
                print(f"Command: {command}")

                # Check if user wants to stop
                if "stop listening" in command or "goodbye" in command:
                    listening_mode = False
                    speak("Okay, I will wait for you to call me again.")
                else:
                    threading.Thread(target=processCommand, args=(command,), daemon=True).start()
    except sr.WaitTimeoutError:
        pass
    except sr.UnknownValueError:
        print("Didn't catch that.")
    except sr.RequestError as e:
        print(f"API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")       

def listen_loop():
    while True:
        listen_and_process()

# GUI setup
def draw_realistic_robot(canvas):
    head = canvas.create_oval(100, 20, 200, 100, fill="#222222", outline="#00ffff", width=2)
    left_eye = canvas.create_oval(125, 45, 135, 55, fill="#00ffff", outline="")
    right_eye = canvas.create_oval(165, 45, 175, 55, fill="#00ffff", outline="")
    body = canvas.create_rectangle(115, 100, 185, 200, fill="#1a1a1a", outline="#00ffff", width=2)
    led = canvas.create_oval(145, 140, 155, 150, fill="red", outline="")
    left_arm = canvas.create_line(115, 120, 70, 160, width=6, fill="#444444")
    right_arm = canvas.create_line(185, 120, 230, 160, width=6, fill="#444444")
    left_leg = canvas.create_line(130, 200, 130, 240, width=6, fill="#444444")
    right_leg = canvas.create_line(170, 200, 170, 240, width=6, fill="#444444")
    mouth = canvas.create_rectangle(140, 70, 160, 80, fill="#00cccc", outline="")
    bubble = canvas.create_text(150, 10, text="", fill="#00FFCC", font=("Arial", 10, "bold"))
    return {
        "head": head, "left_eye": left_eye, "right_eye": right_eye,
        "body": body, "led": led, "left_arm": left_arm, "right_arm": right_arm,
        "left_leg": left_leg, "right_leg": right_leg,
        "mouth": mouth, "bubble": bubble
    }

def animate_robot(canvas, parts, state):
    dx = 3 * (-1 if state["angle"] % 2 == 0 else 1)
    canvas.move(parts["left_arm"], dx, 0)
    canvas.move(parts["right_arm"], -dx, 0)

    if state["angle"] % 5 == 0:
        state["blink"] = not state["blink"]
        eye_color = "#000000" if state["blink"] else "#00ffff"
        canvas.itemconfig(parts["left_eye"], fill=eye_color)
        canvas.itemconfig(parts["right_eye"], fill=eye_color)

    if state["speaking"]:
        if state["angle"] % 2 == 0:
            canvas.coords(parts["mouth"], 140, 68, 160, 86)
        else:
            canvas.coords(parts["mouth"], 140, 70, 160, 80)
    else:
        canvas.coords(parts["mouth"], 140, 70, 160, 80)

    led_color = "#ff0000" if state["angle"] % 2 == 0 else "#ff6666"
    canvas.itemconfig(parts["led"], fill=led_color)

    if state["called"]:
        canvas.move(parts["head"], -2 if state["angle"] % 4 == 0 else 2, 0)
        if state["angle"] > 15:
            state["called"] = False

    if state["angle"] % 6 == 0:
        canvas.move(parts["left_leg"], 0, 1)
        canvas.move(parts["right_leg"], 0, -1)
    elif state["angle"] % 6 == 3:
        canvas.move(parts["left_leg"], 0, -1)
        canvas.move(parts["right_leg"], 0, 1)

    canvas.itemconfig(parts["bubble"], text="I'm listening, Aman..." if state["speaking"] else "")
    state["angle"] += 1
    canvas.after(300, animate_robot, canvas, parts, state)

def run_gui():
    def on_start(): threading.Thread(target=listen_loop, daemon=True).start()
    def on_photo_button(): threading.Thread(target=capture_photo, daemon=True).start()
    def on_view_photo(): threading.Thread(target=show_saved_photo, daemon=True).start()

    def on_search():
        query = search_entry.get().strip().lower()
        if not query:
            result_label.config(text="Please enter a question to search.", fg="orange")
            return
        global ques_ans
        ques_ans = load_ques_ans()
        result = ques_ans.get(query)
        if result:
            result_label.config(text=f"Answer: {result}", fg="#00FFCC")
        else:
            result_label.config(text="No match found.", fg="red")

    def toggle_voice():
        global voice_gender
        voice_gender = "male" if voice_gender == "female" else "female"
        gender_label.config(text=f"🎤 Voice: {voice_gender.capitalize()}")

    window = tk.Tk()
    window.title("Aman's Voice Assistant")
    window.geometry("850x750")
    window.configure(bg="#000000")

    # Responsive columns
    for i in range(3):
        window.grid_columnconfigure(i, weight=1)

    try:
        my_photo = Image.open("Aman.jpg.jpg")   # <- keep your photo in same folder with this name
        my_photo = my_photo.resize((150, 150))
        my_photo_tk = ImageTk.PhotoImage(my_photo)

        # Add your photo on top-right side
        my_photo_label = tk.Label(window, image=my_photo_tk, bg="#000000")
        my_photo_label.image = my_photo_tk  # keep reference
        my_photo_label.grid(row=0, column=2, padx=10, pady=10, sticky="ne")
    except Exception as e:
        print(f"Could not load your photo: {e}")


    glow_btn_style = {
        "font": ("Arial", 12, "bold"),
        "bg": "#111111",
        "fg": "#00FFCC",
        "activebackground": "#222222",
        "activeforeground": "#00ffff",
        "highlightbackground": "#00FFFF",
        "highlightthickness": 1,
        "relief": "ridge",
        "bd": 2
    }

    # Title
    tk.Label(window, text="AMAN'S CHATBOT ASSISTANT", font=("Arial", 20, "bold"),
             bg="#000000", fg="#00FFCC", highlightthickness=0)\
        .grid(row=0, column=0, columnspan=3, pady=(20, 5), sticky="n")

    tk.Label(window, text="Created by Aman Kumar [B.TECH(CSE) - LPU]", font=("Arial", 10, "italic"),
             bg="#000000", fg="#00FFCC").grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky="n")

    # Voice & Control Buttons
    tk.Button(window, text="🎙 Start Listening", command=on_start, **glow_btn_style)\
        .grid(row=2, column=0, padx=10, pady=10, sticky="ew", ipadx=40)

    tk.Button(window, text="🔁Switch Voice", command=toggle_voice, **glow_btn_style)\
        .grid(row=2, column=1, padx=10, pady=10, sticky="ew", ipadx=40)

    gender_label = tk.Label(window, text="🎤 Voice: Female", font=("Arial", 12),
                            bg="#000000", fg="#00FFCC")
    gender_label.grid(row=2, column=2, padx=10, pady=10, sticky="ew")

    # Q&A Section
    tk.Label(window, text="Search Q&A", font=("Arial", 13, "bold"),
             bg="#000000", fg="#00FFCC")\
        .grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="ew")

    search_entry = tk.Entry(window, width=50, font=("Arial", 11),
                            bg="#222222", fg="#00FFCC", insertbackground="#00FFCC")
    search_entry.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    tk.Button(window, text="Search", command=on_search, **glow_btn_style)\
        .grid(row=4, column=2, padx=5, sticky="ew", ipadx=20)

    result_label = tk.Label(window, text="", font=("Arial", 11), bg="#000000", fg="#00FFCC",
                            wraplength=600, justify="center")
    result_label.grid(row=5, column=0, columnspan=3, pady=5, sticky="ew")

    # Photo buttons
    tk.Button(window, text="📷 Take Photo", command=on_photo_button, **glow_btn_style)\
        .grid(row=6, column=0, padx=10, pady=10, sticky="ew", ipadx=40)

    tk.Button(window, text="🖼 View Saved Photo", command=on_view_photo, **glow_btn_style)\
        .grid(row=6, column=1, columnspan=2, padx=10, pady=10, sticky="ew", ipadx=40)

    global photo_label
    photo_label = tk.Label(window, bg="#000000")
    photo_label.grid(row=7, column=0, columnspan=3, pady=5)

    update_photo_preview()

    # Robot Canvas
    canvas = tk.Canvas(window, width=300, height=250, bg="#000000", highlightthickness=0)
    canvas.grid(row=8, column=0, columnspan=3, pady=10)

    parts = draw_realistic_robot(canvas)
    animate_robot(canvas, parts, state)
  
    window.mainloop()

if __name__ == "__main__":
    speak("Aman's Voice Assistant is ready.")
    run_gui()
