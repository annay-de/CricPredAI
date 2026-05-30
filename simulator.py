from __future__ import annotations
import json, math, random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
import joblib

OUTCOMES = ["0", "1", "2", "3", "4", "6", "W", "WD", "NB", "LB", "B"]
LEGAL_OUTCOMES = {"0","1","2","3","4","6","W","LB","B"}
EXTRA_OUTCOMES = {"WD","NB"}

ART = Path(__file__).resolve().parent / "artifacts"
MODELS = ART / "models"


def phase_from_over(over: int) -> str:
    if over < 6: return "powerplay"
    if over < 16: return "middle"
    return "death"


def load_artifacts():
    with open(ART / "metadata.json") as f: meta = json.load(f)
    report = pd.read_csv(ART / "model_report.csv") if (ART/"model_report.csv").exists() else pd.DataFrame()
    models = {}
    for p in MODELS.glob("*.joblib"):
        try: models[p.stem] = joblib.load(p)
        except Exception: pass
    return meta, report, models


def vector_input(state: dict, batter: str, bowler: str, batting_team: str, bowling_team: str, venue: str, toss_decision: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "innings": state.get("innings",1), "over": state.get("over",0), "legal_ball": max(1, state.get("legal_ball",1)),
        "team_runs": state.get("runs",0), "team_wicket": state.get("wickets",0),
        "batter_runs": state.get("bat_runs",{}).get(batter,0), "batter_balls": state.get("bat_balls",{}).get(batter,0),
        "phase": phase_from_over(state.get("over",0)), "batting_team": batting_team, "bowling_team": bowling_team,
        "batter": batter, "bowler": bowler, "venue": venue, "toss_decision": toss_decision
    }])


def normalise(d: Dict[str,float]) -> Dict[str,float]:
    arr = np.array([max(0.0, float(d.get(o,0))) for o in OUTCOMES], dtype=float) + 1e-9
    arr = arr / arr.sum()
    return {o: float(arr[i]) for i,o in enumerate(OUTCOMES)}


def get_empirical(priors: dict, batter: str, bowler: str, phase: str) -> Dict[str,float]:
    g = priors.get("global", {})
    ph = priors.get("phase", {}).get(phase, g)
    bp = priors.get("batter_phase", {}).get(f"{batter}||{phase}", ph)
    wp = priors.get("bowler_phase", {}).get(f"{bowler}||{phase}", ph)
    blended = {}
    for o in OUTCOMES:
        blended[o] = 0.45*float(ph.get(o,0)) + 0.30*float(bp.get(o,0)) + 0.25*float(wp.get(o,0))
    return normalise(blended)


def model_probs(model_name: str, models: dict, priors: dict, x: pd.DataFrame, batter: str, bowler: str, phase: str, temperature: float=0.85) -> Dict[str,float]:
    emp = get_empirical(priors, batter, bowler, phase)
    if model_name == "baseline_prior" or model_name not in models or model_name == "calibrated_blend":
        ml = emp
    else:
        try:
            m = models[model_name]
            proba = m.predict_proba(x)[0]
            cls = list(getattr(m, "classes_", OUTCOMES))
            ml = {o: 1e-9 for o in OUTCOMES}
            for c,p in zip(cls, proba):
                c = str(c)
                if c in ml: ml[c] = float(p)
            ml = normalise(ml)
        except Exception:
            ml = emp
    # calibrated blend: ML receives weight, empirical priors keep cricket realism
    w_ml = 0.0 if model_name == "baseline_prior" else 0.45
    raw = {o: w_ml*ml[o] + (1-w_ml)*emp[o] for o in OUTCOMES}
    # Practical calibration caps to avoid silly collapses/extras
    raw["W"] = min(raw["W"], 0.075)
    raw["WD"] = min(raw["WD"], 0.060)
    raw["NB"] = min(raw["NB"], 0.018)
    # smooth via temperature, <1 keeps confident but not extreme after clipping
    arr = np.array([raw[o] for o in OUTCOMES], dtype=float)
    arr = np.power(arr + 1e-12, temperature)
    arr /= arr.sum()
    return {o: float(arr[i]) for i,o in enumerate(OUTCOMES)}


def choose_next_batter(available: List[str], used: List[str], meta: dict, phase: str, wickets: int) -> Optional[str]:
    remaining = [p for p in available if p not in used]
    if not remaining: return None
    roles = meta.get("roles", {})
    def score(p):
        r = roles.get(p,{})
        base = float(r.get("batting_score",0.0))
        role = r.get("role", "batter")
        if wickets >= 6 and role == "bowler": base -= 0.6
        if phase == "death" and role == "all-rounder": base += 0.15
        return base
    return sorted(remaining, key=score, reverse=True)[0]


def choose_bowler(bowlers: List[str], meta: dict, over: int, bowler_overs: Dict[str,int], prev_bowler: Optional[str]) -> Tuple[str,str]:
    phase = phase_from_over(over)
    roles = meta.get("roles", {})
    candidates = [b for b in bowlers if bowler_overs.get(b,0) < 4 and b != prev_bowler]
    if not candidates:
        candidates = [b for b in bowlers if bowler_overs.get(b,0) < 4] or bowlers
    def score(b):
        r = roles.get(b,{})
        base = float(r.get("bowling_score",0.0))
        balls = float(r.get("bowl_balls",0))
        if r.get("role") in ["bowler","all-rounder"]: base += 0.4
        if phase == "death": base += 0.10*np.log1p(balls)
        if phase == "powerplay": base += 0.05*np.log1p(balls)
        return base
    chosen = sorted(candidates, key=score, reverse=True)[0]
    reason = f"selected for {phase} based on role, historical bowling usage, phase fit, and four-over limit"
    return chosen, reason


def rotate_strike(striker, non_striker):
    return non_striker, striker


def outcome_to_runs(out: str, priors: dict, rng: np.random.Generator, free_hit: bool=False) -> Tuple[int,int,bool,str,bool]:
    """returns runs_total, batter_runs, wicket, extra_type, legal_ball"""
    if out == "W" and free_hit:
        out = "1" if rng.random() < 0.45 else "0"
    if out in ["0","1","2","3","4","6"]:
        br = int(out); return br, br, False, "", True
    if out == "W": return 0, 0, True, "", True
    if out in ["WD","NB"]:
        vals = priors.get("extra_runs",{}).get(out,[1])
        extra = int(rng.choice(vals)) if vals else 1
        extra = max(1, min(extra, 7))
        return extra, max(0, extra-1 if out == "NB" else 0), False, "wides" if out=="WD" else "noballs", False
    if out in ["LB","B"]:
        vals = priors.get("extra_runs",{}).get(out,[1])
        extra = int(rng.choice(vals)) if vals else 1
        extra = max(1, min(extra, 4))
        return extra, 0, False, "legbyes" if out=="LB" else "byes", True
    return 0,0,False,"",True


def simulate_innings(team_name: str, opponent: str, batting_xi: List[str], bowling_xi: List[str], models:dict, meta:dict, model_name:str,
                     venue="Unknown", pitch="balanced", weather="clear", toss_decision="bat", innings=1, target:Optional[int]=None,
                     seed:Optional[int]=None, commentary=False) -> dict:
    rng = np.random.default_rng(seed)
    priors = models.get("baseline_prior", {})
    batters = batting_xi[:]
    # eligible bowlers: historical bowlers/all-rounders first, fallback to last 6 players
    roles = meta.get("roles",{})
    bowlers = [p for p in bowling_xi if roles.get(p,{}).get("role") in ["bowler","all-rounder"] and roles.get(p,{}).get("bowl_balls",0) >= 30]
    if len(bowlers) < 5: bowlers = (bowlers + bowling_xi[-7:])[:7]

    striker, non_striker = batters[0], batters[1]
    used_batters = [striker, non_striker]
    bat = {p:{"R":0,"B":0,"4s":0,"6s":0,"out":"not out"} for p in batters}
    bowl = {p:{"O_balls":0,"R":0,"W":0,"WD":0,"NB":0} for p in bowlers}
    rows=[]; fow=[]; over_summary=[]
    state = {"innings":innings,"over":0,"legal_ball":1,"runs":0,"wickets":0,"bat_runs":{},"bat_balls":{}}
    over = 0; prev_bowler=None; current_bowler=None; legal_in_over=0; free_hit=False
    over_runs=0; over_wkts=0; extra_seq=0

    while over < 20 and state["wickets"] < 10:
        if legal_in_over == 0:
            current_bowler, reason = choose_bowler(bowlers, meta, over, {k:v["O_balls"]//6 for k,v in bowl.items()}, prev_bowler)
            if current_bowler not in bowl: bowl[current_bowler] = {"O_balls":0,"R":0,"W":0,"WD":0,"NB":0}
            over_runs=0; over_wkts=0; extra_seq=0
        phase = phase_from_over(over)
        state.update({"over":over,"legal_ball":legal_in_over+1})
        x = vector_input(state, striker, current_bowler, team_name, opponent, venue, toss_decision)
        p = model_probs(model_name, models, priors, x, striker, current_bowler, phase)
        # conditions nudge, modest and transparent
        if pitch == "bowling-friendly": p["W"] = min(0.09, p["W"]*1.12)
        if pitch == "batting-friendly":
            p["4"] *= 1.08; p["6"] *= 1.08; p["W"] *= 0.90
        if weather in ["humid/dewy", "rain-threat"]: p["WD"] *= 1.08; p["NB"] *= 1.05
        p = normalise(p)
        out = rng.choice(OUTCOMES, p=[p[o] for o in OUTCOMES])
        runs, bruns, wicket, extra_type, legal = outcome_to_runs(out, priors, rng, free_hit=free_hit)
        if free_hit and legal: free_hit=False
        if out == "NB": free_hit=True

        state["runs"] += runs; over_runs += runs
        if current_bowler in bowl:
            bowl[current_bowler]["R"] += runs if extra_type not in ["legbyes","byes"] else 0
            if out == "WD": bowl[current_bowler]["WD"] += 1
            if out == "NB": bowl[current_bowler]["NB"] += 1
        if bruns:
            bat[striker]["R"] += bruns
            if bruns == 4: bat[striker]["4s"] += 1
            if bruns == 6: bat[striker]["6s"] += 1
        if legal:
            bat[striker]["B"] += 1
            bowl[current_bowler]["O_balls"] += 1
            state["bat_balls"][striker] = bat[striker]["B"]
            legal_in_over += 1
        state["bat_runs"][striker] = bat[striker]["R"]

        dismissed = ""
        if wicket:
            state["wickets"] += 1; over_wkts += 1
            bowl[current_bowler]["W"] += 1
            dismissed = striker
            bat[striker]["out"] = f"c/b {current_bowler}" if rng.random()<0.55 else f"b {current_bowler}"
            fow.append({"wicket":state["wickets"], "score":state["runs"], "over":f"{over}.{legal_in_over}", "player":striker})
            nb = choose_next_batter(batters, used_batters, meta, phase, state["wickets"])
            if nb is None or state["wickets"] >= 10:
                pass
            else:
                striker = nb; used_batters.append(nb)

        if legal:
            label = f"{over}.{legal_in_over}"
        else:
            extra_seq += 1
            suffix = "wd" if out == "WD" else "nb"
            label = f"{over}.{legal_in_over+1}{suffix}{extra_seq}"
        comm = ""
        if commentary:
            if out == "W": comm = f"{current_bowler} strikes, {dismissed} is gone at a crucial stage."
            elif out == "6": comm = f"{striker} launches it for six."
            elif out == "4": comm = f"{striker} finds the boundary."
            elif out in ["WD","NB"]: comm = f"Extra conceded by {current_bowler}; the legal ball count stays unchanged."
            else: comm = f"{current_bowler} to {striker}, {runs} run{'s' if runs!=1 else ''}."
        rows.append({"ball":label,"over":over,"legal_ball_in_over":legal_in_over,"phase":phase,"bowler":current_bowler,"batter":striker,
                     "outcome":out,"runs":runs,"batter_runs":bruns,"extras":max(0,runs-bruns),"extra_type":extra_type,"wicket":wicket,
                     "score":state["runs"],"wickets":state["wickets"],"p_wicket":round(p["W"],4),"p_boundary":round(p["4"]+p["6"],4),
                     "p_extra":round(p["WD"]+p["NB"]+p["LB"]+p["B"],4),"bowler_reason": reason if legal_in_over<=1 else "", "commentary":comm})

        if legal and bruns % 2 == 1: striker, non_striker = rotate_strike(striker, non_striker)
        if legal_in_over == 6:
            over_summary.append({"over":over+1,"bowler":current_bowler,"runs":over_runs,"wickets":over_wkts,"score":f"{state['runs']}/{state['wickets']}"})
            striker, non_striker = rotate_strike(striker, non_striker)
            prev_bowler=current_bowler; current_bowler=None; legal_in_over=0; over += 1
        if target is not None and state["runs"] >= target:
            break

    def overs_str(balls): return f"{balls//6}.{balls%6}"
    batting_card = []
    for p in batters:
        r=bat[p]
        if r["B"] or r["R"] or p in used_batters:
            sr = 100*r["R"]/r["B"] if r["B"] else 0
            batting_card.append({"Batter":p,"Dismissal":r["out"],"R":r["R"],"B":r["B"],"4s":r["4s"],"6s":r["6s"],"SR":round(sr,1)})
    bowling_card = []
    for p,r in bowl.items():
        if r["O_balls"] or r["R"]:
            eco = 6*r["R"]/r["O_balls"] if r["O_balls"] else 0
            bowling_card.append({"Bowler":p,"O":overs_str(r["O_balls"]),"R":r["R"],"W":r["W"],"WD":r["WD"],"NB":r["NB"],"Econ":round(eco,2)})
    end_reason = "target reached" if target is not None and state["runs"] >= target else ("all out" if state["wickets"]>=10 else "20 overs completed")
    rules = {"no_bowler_over_4": all(v["O_balls"]<=24 for v in bowl.values()), "legal_balls_max_120": sum(v["O_balls"] for v in bowl.values())<=120, "wickets_max_10": state["wickets"]<=10}
    return {"team":team_name,"runs":state["runs"],"wickets":state["wickets"],"overs":overs_str(sum(v["O_balls"] for v in bowl.values())),"end_reason":end_reason,
            "batting_card":pd.DataFrame(batting_card),"bowling_card":pd.DataFrame(bowling_card),"fall_of_wickets":pd.DataFrame(fow),
            "ball_by_ball":pd.DataFrame(rows),"over_summary":pd.DataFrame(over_summary),"rules":rules}


def simulate_match(team1, team2, xi1, xi2, models, meta, model_name, venue, pitch, weather, toss_winner, toss_decision, seed=None, commentary=False):
    # toss decides batting order
    if toss_decision == "bat":
        bat_first = toss_winner
    else:
        bat_first = team2 if toss_winner == team1 else team1
    if bat_first == team1:
        first = simulate_innings(team1, team2, xi1, xi2, models, meta, model_name, venue,pitch,weather,toss_decision,1,None,seed,commentary)
        second = simulate_innings(team2, team1, xi2, xi1, models, meta, model_name, venue,pitch,weather,toss_decision,2,first["runs"]+1,None if seed is None else seed+1,commentary)
    else:
        first = simulate_innings(team2, team1, xi2, xi1, models, meta, model_name, venue,pitch,weather,toss_decision,1,None,seed,commentary)
        second = simulate_innings(team1, team2, xi1, xi2, models, meta, model_name, venue,pitch,weather,toss_decision,2,first["runs"]+1,None if seed is None else seed+1,commentary)
    if second["runs"] >= first["runs"]+1:
        winner = second["team"]; margin = f"by {10-second['wickets']} wickets"
    elif first["runs"] > second["runs"]:
        winner = first["team"]; margin = f"by {first['runs']-second['runs']} runs"
    else:
        winner = "Tie"; margin = "scores level"
    return {"first":first,"second":second,"winner":winner,"margin":margin}


def simulate_distribution(n, *args, **kwargs):
    rows=[]
    base_seed = kwargs.pop("seed", None)
    for i in range(n):
        res = simulate_match(*args, seed=None if base_seed is None else base_seed+i, commentary=False, **kwargs)
        rows.append({"sim":i+1,"winner":res["winner"],"first_runs":res["first"]["runs"],"second_runs":res["second"]["runs"],"first_wickets":res["first"]["wickets"],"second_wickets":res["second"]["wickets"]})
    return pd.DataFrame(rows)
    
