# audio_download.py

import argparse
import os
import sys
from gtts import gTTS
import logging # Add this line

# Configure logging to show messages immediately
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s') # Add this line

# Your list of words
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

def download_audio_files(output_folder: str, words: list[str]):
    """
    Downloads audio files for each word in the list using gTTS.
    Audio files are saved as <word>.mp3 in the specified output_folder.
    """
    try:
        from gtts import gTTS
    except ImportError:
        print("Error: gTTS not installed. Please install it using: pip install gtts", file=sys.stderr)
        sys.exit(1)

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    print(f"Downloading audio files to: '{output_folder}'")

    for i, word in enumerate(words):
        filename = f"{word.lower()}.mp3" # Using lowercase for filenames
        filepath = os.path.join(output_folder, filename)

        if os.path.exists(filepath):
            print(f"Skipping {word} ({i+1}/{len(words)}) - '{filename}' already exists.")
            continue

        try:
            print(f"Downloading {word} ({i+1}/{len(words)}) …", end=" ", flush=True)
            tts = gTTS(text=word, lang="en", slow=True)
            tts.save(filepath)
            print(f"✓ Saved to '{filename}'")
        except Exception as e:
            print(f"✗ Failed to download {word}: {e}", file=sys.stderr)

    print("\nDownload process complete.")

def main():
    parser = argparse.ArgumentParser(description="Download audio files for a list of words using Google TTS.")
    parser.add_argument("folder_name", help="The name of the folder where audio files will be downloaded.")
    args = parser.parse_args()

    download_audio_files(args.folder_name, WORDS)

if __name__ == "__main__":
    main()