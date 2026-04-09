# spelling_trainer.py

import argparse
import os
import random
import sys
import time
from gtts import gTTS # type: ignore
import subprocess # For ffplay playback

# --- Your List of Words ---
WORDS = [
    "Bears", "Canal", "Clear", "Taste", "Flair", "Gulls", "Heart", "Honey", "Music", "Pools",
    "Pumas", "Ruins", "Savor", "Skies", "Spice", "Colour", "Animal", "Apogee", "Heritage", "Barley",
    "Brands", "Bridge", "Vendors", "Condor", "Drinks", "Flavor", "Forest", "Fusion", "Gentle", "Hotels",
    "Houses", "Lagoon", "Lilies", "Llamas", "Lupine", "Metals", "Wetlands", "Quench", "Refuge", "Renown",
    "Scenic", "Serene", "Served", "Spices", "Stalls", "Tapirs", "Thirst", "Traded", "Crafted", "Bargain",
    "Culture", "Dessert", "Facades", "Farming", "Fitness", "Flowers", "Gallery", "Fountains", "Pathways", "Immerse",
    "Objects", "Orchids", "Pastries", "Pyramid", "Rabbits", "Springs", "Streets", "Landscape", "Velvety", "Altitude",
    "Artisans", "Balanced", "Bleached", "Charming", "Colonial", "Colourful", "Convents", "Costumes", "Majestic", "National",
    "Panorama", "Plantain", "Plateaus", "Restored", "Richness", "Valerian", "Benchmark", "Displayed", "Education", "Guardians",
    "Intensity", "Nightlife", "Preserved", "Sugarcane", "Sweetness", "Testimony", "Balconyway", "Comparable", "Emblematic", "Experience",
    "Gastronomy", "Guesthouse", "Indigenous", "Caffeinated", "Cobblestone", "Festivities", "Handicrafts", "Hypothermal", "Inhabitants", "Extraordinary",
    "Picturesque", "Processions", "Supermarket", "Therapeutic", "Floriculture", "Performance", "Complementary", "Environmental", "Sustainability", "Traditionalism"
]
# --- End of Words List ---


def ensure_audio_folder(folder_name: str, words_list: list[str]):
    """
    Ensures that the audio files exist in the specified folder.
    If not, it downloads them using gTTS.
    """
    try:
        from gtts import gTTS
    except ImportError:
        print("Error: gTTS not installed. Please install it using: pip install gtts", file=sys.stderr)
        sys.exit(1)

    os.makedirs(folder_name, exist_ok=True)
    missing_files = []

    print(f"Checking for audio files in '{folder_name}'...")
    for word in words_list:
        filename = f"{word.lower()}.mp3"
        filepath = os.path.join(folder_name, filename)
        if not os.path.exists(filepath):
            missing_files.append(word)

    if missing_files:
        print(f"{len(missing_files)} missing audio files found. Downloading them now:")
        for i, word in enumerate(missing_files):
            filename = f"{word.lower()}.mp3"
            filepath = os.path.join(folder_name, filename)
            try:
                print(f"  Downloading {word} ({i+1}/{len(missing_files)}) …", end=" ", flush=True)
                tts = gTTS(text=word, lang="en", slow=True)
                tts.save(filepath)
                print(f"✓ Saved to '{filename}'")
            except Exception as e:
                print(f"✗ Failed to download {word}: {e}", file=sys.stderr)
        print("Finished downloading missing audio files.")
    else:
        print("All audio files are present.")


def play_word_audio(word: str, audio_folder: str):
    """Plays the audio file for a given word using ffplay via subprocess."""
    filepath = os.path.join(audio_folder, f"{word.lower()}.mp3")
    if not os.path.exists(filepath):
        print(f"Error: Audio file for '{word}' not found at '{filepath}'. Please ensure all audio files are downloaded.", file=sys.stderr)
        return False
    try:
        # ffplay is part of ffmpeg and can play MP3s directly
        # -nodisp means no video window, -autoexit means quit after playback
        command = ["ffplay", "-nodisp", "-autoexit", filepath]
        
        # Use subprocess.run to execute the command.
        # Set timeout to prevent hanging if ffplay itself crashes or hangs.
        # capture_output and text are for capturing output for debugging,
        # but if the segfault was related to how python handled the output streams,
        # it might be safer to let ffplay manage its own I/O, though unlikely for this kind of crash.
        # We'll keep them for error messages.
        process = subprocess.run(command, capture_output=True, text=True, timeout=10)

        if process.returncode != 0:
            if "ffplay not found" in process.stderr.lower() or "ffplay not found" in process.stdout.lower():
                print("Error: 'ffplay' command not found. Please ensure FFmpeg is installed and in your PATH.", file=sys.stderr)
            else:
                print(f"Error: ffplay exited with code {process.returncode}. Stderr: {process.stderr}", file=sys.stderr)
            return False

        return True
    except FileNotFoundError:
        print("Error: 'ffplay' command not found. Please ensure FFmpeg is installed and in your PATH.", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(f"Error: ffplay timed out while playing '{word}'.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error playing audio for '{word}': {e}", file=sys.stderr)
        print("--- Troubleshooting Audio Playback (ffplay) ---", file=sys.stderr)
        print("1. Ensure 'ffmpeg' (which includes 'ffplay') is installed system-wide: sudo apt-get install ffmpeg", file=sys.stderr)
        print("2. Verify the MP3 file itself is not corrupted and can be played by other players (e.g., 'ffplay your_word.mp3' directly in terminal).", file=sys.stderr)
        print("-----------------------------------------------------", file=sys.stderr)
        return False


def spelling_game(audio_folder: str, words_to_use: list[str]):
    """Runs the interactive spelling game."""
    print("\n--- Welcome to the Spelling Trainer! ---")
    print(f"Words loaded: {len(words_to_use)}")
    print("I will say a word, and you type it. Type 'quit' to exit.")

    score = 0
    total_words = 0
    correctly_spelled_words = set()
    incorrectly_spelled_words = set()

    # Create a shuffleable list of words for the current session
    session_words = list(words_to_use)
    random.shuffle(session_words)

    while True: # Main game loop for each word
        if not session_words:
            print("\nYou've gone through all the words in this session! Starting a new round with shuffled words.")
            session_words = list(words_to_use)
            random.shuffle(session_words)

        word_to_spell = session_words.pop(0) # Get a word and remove it from the list

        print(f"\nYour word is: (Press Enter to hear the word again)")
        input(">>> Press Enter to hear the word <<<") # Initial prompt to press Enter

        actual_user_input = "" # Initialize for safety
        word_processed_successfully = False # Flag to track if we got a valid answer or user quit/skipped

        while True: # Loop for playing audio and getting user input (including replays/repeats)
            if not play_word_audio(word_to_spell, audio_folder):
                print("Could not play audio. Skipping to next word.")
                break # Exit inner loop, proceed to next word in outer loop

            user_input_attempt = input("Type the word (or 'replay' to hear again, 'quit' to exit, just Enter to repeat): ").strip()

            if user_input_attempt.lower() == 'quit':
                actual_user_input = user_input_attempt # Assign 'quit' to handle outer loop exit
                word_processed_successfully = True # User made a choice
                break # Exit inner loop

            elif user_input_attempt.lower() == 'replay' or user_input_attempt == '': # Handle 'replay' OR empty Enter
                print("Playing word again...")
                # Continue the inner loop to play audio again without processing an answer
                continue

            else: # User typed a word
                actual_user_input = user_input_attempt
                word_processed_successfully = True # Input was received and not 'replay' or empty
                break # Exit inner loop, proceed with checking the answer

        # After the inner loop, check if we should continue to the next word or quit
        if not word_processed_successfully:
            if actual_user_input.lower() == 'quit': # User explicitly quit from inside the inner loop
                break # Exit the main game loop
            continue # Skip to the next word if audio failed or user just kept hitting enter/replay

        # --- Process the answer if a valid input was received ---
        if actual_user_input.lower() == 'quit': # Double-check here just in case (should be caught above)
            break

        total_words += 1

        if actual_user_input.lower() == word_to_spell.lower():
            score += 1
            print(f"Correct! 🎉")
            correctly_spelled_words.add(word_to_spell.lower())
            if word_to_spell.lower() in incorrectly_spelled_words:
                incorrectly_spelled_words.remove(word_to_spell.lower())
        else:
            print(f"Incorrect. The correct spelling was: '{word_to_spell}'")
            incorrectly_spelled_words.add(word_to_spell.lower())

        print(f"Current Score: {score}/{total_words}")

    print("\n--- Game Over! ---")
    print(f"Final Score: {score}/{total_words}")
    if correctly_spelled_words:
        print(f"Words you spelled correctly: {', '.join(sorted(list(correctly_spelled_words)))}")
    if incorrectly_spelled_words:
        print(f"Words you had trouble with: {', '.join(sorted(list(incorrectly_spelled_words)))}")
    print("Thanks for playing!")


def main():
    parser = argparse.ArgumentParser(description="Interactive Spelling Trainer.")
    parser.add_argument("audio_folder", help="The folder containing the audio files for the words.")
    args = parser.parse_args()

    # First, ensure all audio files are present or download them
    ensure_audio_folder(args.audio_folder, WORDS)

    # Then, start the game
    spelling_game(args.audio_folder, WORDS)

if __name__ == "__main__":
    main()