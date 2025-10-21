def scorecard(scores, weights):
    # scores: dict T A S V O E (0..100)
    Up = (scores["T"]*weights["T"] + scores["A"]*weights["A"] + scores["S"]*weights["S"]
          + scores["V"]*weights["V"] + scores["O"]*weights["O"] + scores["E"]*weights["E"]) / 100.0
    Up = max(0.0, min(100.0, Up))
    Down = 100.0-Up
    edge = (Up-Down)/100.0
    return Up, Down, edge