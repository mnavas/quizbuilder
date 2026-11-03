# spelling_bee_audio

Drop one MP3 per word here, named `<word>.mp3` (e.g. `necessary.mp3`), to use your own
recordings. Any word without a matching file is generated automatically with Google TTS
when you run `../seed_audio.py` (requires `pip install gtts`).

The word is taken from the filename, so the file name must exactly match the spelling you
want graded.
