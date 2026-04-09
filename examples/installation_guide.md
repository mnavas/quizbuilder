# Spelling Trainer Installation and Usage Guide

This guide will walk you through setting up and running the interactive Spelling Trainer application on a new Linux computer (specifically tested on Ubuntu/Debian-based systems).

The application allows you to practice spelling from a predefined list of words, playing audio prompts and checking your input.

---

## 1. Prerequisites

Before setting up the Python application, you need to install some system-level dependencies.

### 1.1 Update Package List
First, ensure your system's package list is up to date:

```bash
sudo apt-get update
```

### 1.2 Install Python 3 and Pip
Ensure you have Python 3 and its package installer `pip` installed. This guide assumes Python 3.10+ (your system seems to use 3.12).

```bash
sudo apt-get install python3 python3-pip
```

### 1.3 Install FFmpeg (includes `ffplay`)
The trainer uses `ffplay` (part of the FFmpeg suite) to play audio files.
```bash
sudo apt-get install ffmpeg
```
To verify `ffplay` is installed and in your system's PATH, you can run:
```bash
ffplay -version
```
You should see version information for FFmpeg.

---

## 2. Project Setup

### 2.1 Clone the Repository (or copy files)
If your code is in a Git repository, clone it:
```bash
git clone <your-repository-url>
cd <your-project-directory> # e.g., cd quizbee/examples
```
If you're just copying the files ( `spelling_trainer.py`, `audio_download.py`, `spelling_bee.json`, and any audio files you've already downloaded), place them in your desired project directory.

### 2.2 Create and Activate a Python Virtual Environment
It's best practice to use a virtual environment to manage project dependencies. This prevents conflicts with system-wide Python packages.

```bash
python3 -m venv .venv
source .venv/bin/activate
```
You'll know the virtual environment is active when your terminal prompt changes, usually by `(.venv)` appearing at the beginning.

### 2.3 Install Python Dependencies
With your virtual environment active, install the necessary Python libraries:

```bash
pip install gtts
```
*   `gtts`: Google Text-to-Speech, used for generating audio files if they don't already exist.

**Note:** Unlike previous iterations, this version of the `spelling_trainer.py` no longer requires `playsound`, `simpleaudio`, or `pydub`, simplifying the Python dependencies greatly!

---

## 3. Running the Application

### 3.1 Download Audio Files (Optional, but recommended for first run)
The `spelling_trainer.py` script will automatically download missing audio files when it runs. However, you can also pre-download all audio files using `audio_download.py`. This is good for ensuring all files are present before starting the trainer, or if you want to inspect the generated audio.

From your project directory (with the virtual environment active):

```bash
python audio_download.py spelling_bee_audio
```
This will create a folder named `spelling_bee_audio` in your current directory and download all 120 word audio files into it.

### 3.2 Start the Spelling Trainer
Once the audio files are present (either by pre-downloading or letting the trainer do it), you can start the interactive trainer:

From your project directory (with the virtual environment active):

```bash
python spelling_trainer.py spelling_bee_audio
```
Replace `spelling_bee_audio` with the actual name of the folder where your audio files are stored.

#### How to play:
*   The trainer will pick a random word.
*   It will ask you to press **Enter** to hear the word.
*   After playing the word, it will prompt you to type the word.
*   **To repeat the word:** Type `replay` and press Enter, or simply press **Enter** without typing anything else.
*   **To quit:** Type `quit` and press Enter at any input prompt.

---

## 4. Troubleshooting

### 4.1 `ModuleNotFoundError: No module named 'gtts'`
*   **Solution:** Your Python virtual environment is likely not active, or `gtts` was not installed.
    *   Ensure your virtual environment is active: `source .venv/bin/activate`
    *   Install `gtts`: `pip install gtts`

### 4.2 `Error: 'ffplay' command not found.`
*   **Solution:** FFmpeg (which includes `ffplay`) is not installed or not in your system's PATH.
    *   Install FFmpeg: `sudo apt-get install ffmpeg`
    *   Verify installation: `ffplay -version`

### 4.3 Audio Files Not Downloading (from `audio_download.py` or `spelling_trainer.py`)
*   **Cause:** Network issues, or `gtts` might be temporarily unable to reach Google's TTS service.
*   **Solution:**
    *   Check your internet connection.
    *   Try running the script again after some time.

### 4.4 Audio Doesn't Play, or Plays Silently (even if `ffplay` seems installed)
*   **Cause:** System audio configuration issues, or `ffplay` might be using a non-functional audio output device.
*   **Solution:**
    *   Test `ffplay` directly: `ffplay -nodisp -autoexit /path/to/your/spelling_bee_audio/bears.mp3`
    *   If `ffplay` works directly, the issue might be transient. If it doesn't, check your system's sound settings, volume levels, and ensure your audio output device is correctly configured. You might need to specify an audio device for `ffplay` (e.g., `ffplay -i <file> -acodec pcm_s16le -f s16le -ac 2 -ar 44100 -o /dev/snd/pcmC0D0p`). This is advanced troubleshooting.

### 4.5 General Python Errors / `Segmentation fault`
*   **Cause:** While the `ffplay` approach is robust against Python-library-level segfaults, deep system-level issues can still occur.
*   **Solution:**
    *   Ensure your system is fully updated: `sudo apt-get update && sudo apt-get upgrade`
    *   Restart your computer.
    *   If errors persist, double-check that `ffmpeg` is installed correctly and not corrupted.

---

This guide should provide a clear path for anyone to set up and use your Spelling Trainer.
```