"""
Generate a driving exam practice test JSON for the Quizbee mobile app.
40 multiple-choice questions covering US driving rules, signs, and safety.

Run:  python3 gen_driving_exam.py
Output: driving-exam-example.json  (import via the folder button in the app)
"""

import json, random
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Question bank
# ---------------------------------------------------------------------------

QUESTIONS = [
    # Traffic signs
    ("What does an octagonal red sign mean?",
     ["Stop completely", "Slow down", "Yield", "No entry"],
     "Stop completely"),
    ("What shape is a yield sign?",
     ["Triangle (pointing down)", "Circle", "Octagon", "Diamond"],
     "Triangle (pointing down)"),
    ("A diamond-shaped sign indicates:",
     ["Warning / hazard ahead", "Speed limit", "Stop ahead", "School zone"],
     "Warning / hazard ahead"),
    ("What does a pennant-shaped sign mean?",
     ["No passing zone", "Speed limit change", "Merge ahead", "Lane ends"],
     "No passing zone"),
    ("A white rectangular sign gives:",
     ["Regulatory information (laws)", "Warning of hazards", "Guide information", "Construction zone rules"],
     "Regulatory information (laws)"),
    ("What does a solid yellow center line mean?",
     ["No passing in either direction", "Passing allowed in both directions", "Passing allowed on the left", "Lane is closed"],
     "No passing in either direction"),
    ("A broken yellow center line means:",
     ["Passing is permitted when safe", "No passing allowed", "Road is one-way", "Bike lane ahead"],
     "Passing is permitted when safe"),
    ("What does a flashing red light mean?",
     ["Stop, then proceed when safe", "Slow down", "Proceed with caution", "Road is closed"],
     "Stop, then proceed when safe"),
    ("A flashing yellow light means:",
     ["Slow down and proceed with caution", "Stop completely", "Yield to oncoming traffic", "Lane is closed"],
     "Slow down and proceed with caution"),
    ("What does a green arrow signal mean?",
     ["You may go in the direction of the arrow", "Yield to pedestrians", "Stop and wait", "Right of way is shared"],
     "You may go in the direction of the arrow"),

    # Right of way
    ("At a four-way stop, who goes first?",
     ["The driver who arrived first", "The driver on the right", "The driver on the left", "The driver going straight"],
     "The driver who arrived first"),
    ("When two cars arrive at a four-way stop at the same time, who yields?",
     ["The driver on the left yields to the driver on the right", "The driver on the right yields to the left", "Both stop indefinitely", "The slower car yields"],
     "The driver on the left yields to the driver on the right"),
    ("When turning left at an intersection, you must yield to:",
     ["Oncoming traffic and pedestrians", "Only pedestrians", "Only oncoming traffic", "No one if the light is green"],
     "Oncoming traffic and pedestrians"),
    ("A pedestrian is crossing in a marked crosswalk. You must:",
     ["Stop and yield until they have cleared your lane", "Proceed if they are on the other side", "Honk to warn them", "Speed up to clear the intersection"],
     "Stop and yield until they have cleared your lane"),
    ("When entering a highway from an on-ramp, you must:",
     ["Yield to highway traffic and merge safely", "Have the right of way over highway traffic", "Stop at the end of the ramp", "Flash your lights"],
     "Yield to highway traffic and merge safely"),
    ("An emergency vehicle with lights and siren is approaching. You must:",
     ["Pull to the right and stop", "Speed up to clear the road", "Stop in your current lane", "Slow down by 10 mph"],
     "Pull to the right and stop"),
    ("When a school bus is stopped with flashing red lights, you must:",
     ["Stop regardless of direction (unless divided highway)", "Stop only if behind the bus", "Slow to 15 mph", "Stop only if you are going the same direction"],
     "Stop regardless of direction (unless divided highway)"),

    # Speed and distance
    ("What is the basic speed law?",
     ["Drive at a speed safe for conditions, never faster than is reasonable", "Always drive the posted speed limit exactly", "Drive 5 mph under the speed limit", "Match the speed of surrounding traffic"],
     "Drive at a speed safe for conditions, never faster than is reasonable"),
    ("What is the typical minimum following distance in good conditions?",
     ["3 seconds", "1 second", "5 seconds", "10 feet per 10 mph"],
     "3 seconds"),
    ("In rain or poor visibility, your following distance should:",
     ["Double to at least 6 seconds", "Stay the same", "Reduce to 1 second", "Match the car ahead"],
     "Double to at least 6 seconds"),
    ("The speed limit in a school zone when children are present is typically:",
     ["15–25 mph", "35 mph", "45 mph", "10 mph"],
     "15–25 mph"),
    ("In a residential area with no posted speed limit, you should drive:",
     ["25 mph or less", "35 mph", "15 mph", "Match surrounding traffic"],
     "25 mph or less"),
    ("Hydroplaning occurs when:",
     ["Tires lose contact with the road surface due to water", "Brakes overheat", "Tires are underinflated", "The engine stalls in water"],
     "Tires lose contact with the road surface due to water"),

    # Alcohol and impairment
    ("In most US states, the legal blood alcohol concentration (BAC) limit for drivers 21+ is:",
     ["0.08%", "0.10%", "0.05%", "0.02%"],
     "0.08%"),
    ("For drivers under 21, the BAC limit is typically:",
     ["0.00–0.02% (zero tolerance)", "0.08%", "0.04%", "0.06%"],
     "0.00–0.02% (zero tolerance)"),
    ("Which of the following affects your ability to drive?",
     ["All of the above", "Alcohol", "Prescription medications", "Illegal drugs"],
     "All of the above"),
    ("Driving while impaired by any substance is:",
     ["Illegal and dangerous regardless of the substance", "Only illegal with alcohol", "Legal if prescribed by a doctor", "Only illegal over the BAC limit"],
     "Illegal and dangerous regardless of the substance"),

    # Parking and lane rules
    ("How far from a fire hydrant must you park?",
     ["15 feet", "5 feet", "25 feet", "10 feet"],
     "15 feet"),
    ("You must not park within how many feet of a stop sign?",
     ["30 feet", "15 feet", "10 feet", "50 feet"],
     "30 feet"),
    ("A curb painted red means:",
     ["No stopping, standing, or parking", "Parking for 30 minutes", "Loading zone", "Handicap parking only"],
     "No stopping, standing, or parking"),
    ("When parallel parking, you should be within how many inches of the curb?",
     ["18 inches", "6 inches", "12 inches", "24 inches"],
     "18 inches"),
    ("You may use the HOV (carpool) lane when:",
     ["Your vehicle has the minimum required number of occupants", "The lane is empty", "Driving a hybrid", "You are late"],
     "Your vehicle has the minimum required number of occupants"),
    ("You may not make a U-turn:",
     ["Near the top of a hill or curve where visibility is limited", "On a two-lane road", "At an intersection with no sign prohibiting it", "In a residential area"],
     "Near the top of a hill or curve where visibility is limited"),

    # Safety and equipment
    ("When must you use your headlights?",
     ["From sunset to sunrise and when visibility is under 1000 feet", "Only at night", "Only in rain", "Only on highways"],
     "From sunset to sunrise and when visibility is under 1000 feet"),
    ("Seat belts are required for:",
     ["All occupants in most states", "Only the driver", "Only front-seat passengers", "Only passengers under 18"],
     "All occupants in most states"),
    ("Children under what age/weight typically require a car seat or booster?",
     ["8 years or 4'9\" tall", "5 years or 40 lbs", "12 years", "10 years or 80 lbs"],
     "8 years or 4'9\" tall"),
    ("When should you use your horn?",
     ["Only to warn others of danger", "To greet other drivers", "When frustrated in traffic", "To signal a turn"],
     "Only to warn others of danger"),
    ("If your brakes fail, the first thing you should do is:",
     ["Pump the brakes rapidly and downshift", "Steer off the road immediately", "Turn off the engine", "Pull the parking brake hard"],
     "Pump the brakes rapidly and downshift"),
    ("Before changing lanes, you should:",
     ["Signal, check mirrors, check blind spot, then move", "Signal and move immediately", "Check mirrors only", "Move then signal"],
     "Signal, check mirrors, check blind spot, then move"),
    ("When driving in fog, you should use:",
     ["Low-beam headlights", "High-beam headlights", "Hazard lights while driving", "No lights"],
     "Low-beam headlights"),
]

# ---------------------------------------------------------------------------
# Build payload
# ---------------------------------------------------------------------------

random.shuffle(QUESTIONS)

def tiptap(text: str) -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


blocks = []
for i, (prompt, options, correct) in enumerate(QUESTIONS):
    shuffled = options[:]
    random.shuffle(shuffled)
    blocks.append({
        "title": f"Question {i + 1}",
        "order": i,
        "context_json": None,
        "questions": [{
            "type": "multiple_choice",
            "prompt_json": tiptap(prompt),
            "options_json": [{"id": chr(65 + j), "content_json": tiptap(opt)} for j, opt in enumerate(shuffled)],
            "correct_answer": chr(65 + shuffled.index(correct)),
            "explanation_json": None,
            "media_ref": None,
            "points": 1,
            "tags": ["driving"],
        }],
    })

payload = {
    "quizbee_version": "1.0",
    "exported_at": datetime.now(timezone.utc).isoformat(),
    "test": {
        "title": "US Driver's License Practice Exam",
        "description": "40 multiple-choice questions covering traffic signs, right of way, speed limits, safety rules, and more. 5 random questions per session.",
        "mode": "practice",
        "access": "public",
        "time_limit_minutes": None,
        "allow_multiple_attempts": True,
        "max_attempts": None,
        "randomize_questions": True,
        "randomize_options": True,
        "show_correct_answers": "at_end",
        "passing_score_pct": 70,
        "multiple_select_scoring": "all_or_nothing",
        "draw_count": 5,
        "blocks": blocks,
    },
}

out_path = "driving-exam-example.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"Written {len(QUESTIONS)} questions to {out_path}")
