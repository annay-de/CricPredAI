"""Self-contained match replay theatre component.

Builds a single HTML document (no external JS dependencies) that replays a
simulated match ball by ball: animated scoreboard, over strip, live worm
chart, generated commentary feed, and playback controls. Rendered inside
Streamlit through components.html.
"""

from __future__ import annotations

import json

import pandas as pd


def _ball_records(deliveries: pd.DataFrame) -> list[dict]:
    records = []
    for row in deliveries.itertuples(index=False):
        records.append(
            {
                "lb": int(row.legal_ball_in_over),
                "o": int(row.over),
                "ph": str(row.phase),
                "bw": str(row.bowler),
                "bt": str(row.batter),
                "out": str(row.outcome),
                "r": int(row.runs),
                "br": int(row.batter_runs),
                "et": str(row.extra_type) if str(row.extra_type) != "nan" else "",
                "w": bool(row.wicket),
                "dk": str(row.dismissal_kind),
                "dt": str(row.dismissal),
                "s": int(row.score),
                "wk": int(row.wickets),
                "pw": float(row.p_wicket),
                "pb": float(row.p_boundary),
            }
        )
    return records


def build_payload(result: dict, xi_by_team: dict[str, list[str]], venue: str) -> dict:
    first, second = result["first"], result["second"]
    return {
        "venue": str(venue),
        "winner": str(result["winner"]),
        "margin": str(result["margin"]),
        "target": int(first["runs"]) + 1,
        "innings": [
            {
                "team": str(inn["team"]),
                "runs": int(inn["runs"]),
                "wickets": int(inn["wickets"]),
                "overs": str(inn["overs"]),
                "endReason": str(inn["end_reason"]),
                "order": [str(p) for p in xi_by_team.get(inn["team"], [])],
                "balls": _ball_records(inn["ball_by_ball"]),
            }
            for inn in (first, second)
        ],
    }


def build_replay_html(payload: dict) -> str:
    data = json.dumps(payload).replace("</", "<\\/")
    return _TEMPLATE.replace("__PAYLOAD__", data)


_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;500;600;700;800&family=Newsreader:ital,opsz,wght@1,6..72,400;1,6..72,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0B0F0C; --pit:#10150F; --panel:#131A11; --panel2:#0E130D;
  --ink:#EDEAD9; --mut:#8B9182; --dim:#5A6152;
  --lime:#D6F546; --org:#FF7A3D; --red:#FF4438; --gold:#E8C46B;
  --line:rgba(237,234,217,0.13); --line2:rgba(237,234,217,0.07);
  --mono:"IBM Plex Mono",ui-monospace,monospace;
  --disp:"Anton",system-ui,sans-serif;
  --body:"Archivo",system-ui,sans-serif;
  --serif:"Newsreader",Georgia,serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;color:var(--ink);font-family:var(--body);height:100%}
.stage{
  position:relative;height:100%;min-height:640px;display:flex;flex-direction:column;
  background:
    radial-gradient(120% 60% at 50% -10%, rgba(214,245,70,0.055), transparent 60%),
    linear-gradient(180deg,#0D120D 0%, #0B0F0C 100%);
  border:1px solid var(--line);
  overflow:hidden;
}
.stage::before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.5;z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3CfeComponentTransfer%3E%3CfeFuncA type='linear' slope='0.05'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E");}
.stage>*{position:relative;z-index:1}

/* ---------- top strip ---------- */
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:10px 16px;border-bottom:1px dashed var(--line);}
.topbar .tag{font:600 10px/1 var(--mono);letter-spacing:.22em;color:var(--mut);text-transform:uppercase}
.topbar .live{display:flex;align-items:center;gap:7px;font:600 10px/1 var(--mono);letter-spacing:.22em;color:var(--lime)}
.live .pip{width:7px;height:7px;background:var(--lime);border-radius:50%;animation:pip 1.1s ease-in-out infinite}
.live.done{color:var(--gold)} .live.done .pip{background:var(--gold);animation:none}
@keyframes pip{0%,100%{opacity:1}50%{opacity:.25}}
.phasechip{font:600 10px/1 var(--mono);letter-spacing:.2em;color:#0B0F0C;background:var(--lime);
  padding:5px 9px;text-transform:uppercase}
.phasechip.middle{background:var(--gold)} .phasechip.death{background:var(--org)}

/* ---------- scoreboard ---------- */
.board{display:grid;grid-template-columns:minmax(320px,1.15fr) minmax(0,1fr);gap:0;border-bottom:1px solid var(--line)}
.scorecell{padding:16px 20px 14px;border-right:1px dashed var(--line);position:relative;overflow:hidden}
.batting-team{font:700 12px/1.1 var(--body);letter-spacing:.18em;text-transform:uppercase;color:var(--mut);display:flex;gap:8px;align-items:center}
.batting-team b{color:var(--ink)}
.teamdot{width:9px;height:9px;flex:none}
.bigscore{display:flex;align-items:baseline;gap:14px;margin-top:6px}
.bigscore .runs{font:400 64px/0.95 var(--disp);letter-spacing:.01em;color:var(--ink);font-variant-numeric:tabular-nums}
.bigscore .oversbox{font:500 13px/1.5 var(--mono);color:var(--mut)}
.bigscore .oversbox b{color:var(--ink);font-weight:600}
.chaseline{margin-top:8px;font:500 12px/1.4 var(--mono);color:var(--mut)}
.chaseline b{color:var(--org)}
.chaseline .ok{color:var(--lime)}
/* players */
.players{padding:12px 20px;display:flex;flex-direction:column;gap:0;justify-content:center}
.prow{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:5.5px 0;border-bottom:1px solid var(--line2);font-size:13px}
.prow:last-child{border-bottom:none}
.prow .who{display:flex;gap:8px;align-items:baseline;min-width:0}
.prow .nm{font-weight:600;letter-spacing:.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow .role{font:500 9px/1 var(--mono);letter-spacing:.18em;color:var(--dim);text-transform:uppercase}
.prow .fig{font:500 13px/1 var(--mono);color:var(--ink);white-space:nowrap}
.prow .fig span{color:var(--mut)}
.prow.striker .nm::after{content:" *";color:var(--lime)}
/* over strip */
.overstrip{grid-column:1/-1;display:flex;align-items:center;gap:10px;padding:10px 20px;border-top:1px dashed var(--line);min-height:52px;overflow:hidden}
.overstrip .lbl{font:600 9px/1.2 var(--mono);letter-spacing:.2em;color:var(--dim);text-transform:uppercase;flex:none;width:52px}
.dots{display:flex;gap:6px;align-items:center;flex-wrap:nowrap}
.dot{min-width:26px;height:26px;padding:0 5px;display:inline-flex;align-items:center;justify-content:center;
  font:600 11px/1 var(--mono);border:1px solid var(--line);color:var(--mut);flex:none}
.dot.r0{color:var(--dim)}
.dot.r4{background:rgba(214,245,70,.14);border-color:rgba(214,245,70,.6);color:var(--lime)}
.dot.r6{background:var(--lime);border-color:var(--lime);color:#0B0F0C;font-weight:700}
.dot.rw{background:var(--red);border-color:var(--red);color:#fff;font-weight:700}
.dot.rx{border-style:dashed;color:var(--gold)}
.dot.now{animation:pop .3s ease}
.prevover{opacity:.38}
@keyframes pop{0%{transform:scale(.4)}70%{transform:scale(1.18)}100%{transform:scale(1)}}

/* ---------- middle: worm + commentary ---------- */
.mid{flex:1;display:grid;grid-template-columns:minmax(0,1.6fr) minmax(260px,1fr);min-height:0}
.wormwrap{position:relative;border-right:1px dashed var(--line);min-height:180px}
.wormwrap canvas{position:absolute;inset:0;width:100%;height:100%}
.commwrap{display:flex;flex-direction:column;min-height:0;background:var(--panel2)}
.commhead{font:600 9px/1 var(--mono);letter-spacing:.24em;color:var(--dim);text-transform:uppercase;
  padding:10px 14px;border-bottom:1px dashed var(--line)}
.comm{flex:1;overflow-y:auto;padding:6px 14px 12px;scrollbar-width:thin;scrollbar-color:#2A3226 transparent}
.centry{padding:7px 0;border-bottom:1px solid var(--line2);animation:rise .35s ease}
.centry .cb{font:600 10px/1 var(--mono);color:var(--dim);margin-right:8px}
.centry .ct{font:500 13.5px/1.45 var(--serif);font-style:italic;color:#C9C6B4}
.centry.big .ct{color:var(--ink)}
.centry.wkt .cb{color:var(--red)}
.centry.wkt .ct{color:#FFB4AE}
.centry.four .cb{color:var(--lime)} .centry.six .cb{color:var(--lime)}
.centry.mile .ct{color:var(--gold)}
@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}

/* ---------- flash overlay ---------- */
.flash{position:absolute;inset:0;display:none;align-items:center;justify-content:center;flex-direction:column;gap:6px;
  pointer-events:none;z-index:5}
.flash.show{display:flex;animation:flashin .82s cubic-bezier(.2,.9,.25,1) both}
.flash .fw{font:400 clamp(60px,14vw,120px)/0.9 var(--disp);letter-spacing:.04em;color:var(--lime);
  text-shadow:0 0 60px rgba(214,245,70,.4)}
.flash.wkt .fw{color:var(--red);text-shadow:0 0 60px rgba(255,68,56,.45)}
.flash .fs{font:600 12px/1.4 var(--mono);letter-spacing:.14em;color:var(--ink);text-transform:uppercase;
  background:rgba(11,15,12,.85);padding:6px 12px;max-width:80%;text-align:center}
@keyframes flashin{0%{opacity:0;transform:scale(.7)}18%{opacity:1;transform:scale(1.04)}30%{transform:scale(1)}78%{opacity:1}100%{opacity:0}}

/* ---------- interstitial cards ---------- */
.card{position:absolute;inset:0;z-index:6;display:none;align-items:center;justify-content:center;flex-direction:column;
  background:rgba(11,15,12,.92);backdrop-filter:blur(2px);text-align:center;padding:24px}
.card.show{display:flex;animation:rise .4s ease}
.card .k{font:600 11px/1 var(--mono);letter-spacing:.3em;color:var(--mut);text-transform:uppercase}
.card .h{font:400 clamp(34px,7vw,64px)/1.02 var(--disp);letter-spacing:.02em;margin:14px 0 10px;text-transform:uppercase}
.card .h .win{color:var(--lime)}
.card .s{font:500 13px/1.6 var(--mono);color:var(--mut);max-width:520px}
.card .s b{color:var(--ink)}
.card button{margin-top:22px}
.stamp{position:absolute;right:8%;top:12%;transform:rotate(9deg);border:2px solid var(--gold);color:var(--gold);
  font:600 11px/1 var(--mono);letter-spacing:.3em;padding:9px 14px;text-transform:uppercase;opacity:.85}

/* ---------- controls ---------- */
.controls{display:flex;align-items:center;gap:10px;padding:10px 14px;border-top:1px solid var(--line);background:var(--panel2)}
button{font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--ink);
  background:transparent;border:1px solid var(--line);padding:9px 13px;cursor:pointer;transition:all .12s ease}
button:hover{border-color:var(--lime);color:var(--lime)}
button.primary{background:var(--lime);border-color:var(--lime);color:#0B0F0C}
button.primary:hover{background:#E4FF66;color:#0B0F0C}
button.spd.on{background:var(--ink);border-color:var(--ink);color:#0B0F0C}
.scrub{flex:1;display:flex;align-items:center;gap:10px;min-width:120px}
.scrub input{flex:1;appearance:none;-webkit-appearance:none;height:2px;background:var(--line);outline:none;cursor:pointer}
.scrub input::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:13px;height:13px;background:var(--lime);border:none;border-radius:0;cursor:pointer}
.scrub input::-moz-range-thumb{width:13px;height:13px;background:var(--lime);border:none;border-radius:0;cursor:pointer}
.clock{font:500 11px/1 var(--mono);color:var(--mut);white-space:nowrap}
@media (max-width:760px){
  .board{grid-template-columns:1fr}
  .scorecell{border-right:none;border-bottom:1px dashed var(--line)}
  .mid{grid-template-columns:1fr}
  .commwrap{display:none}
  .bigscore .runs{font-size:48px}
}
</style>
</head>
<body>
<div class="stage" id="stage">
  <div class="topbar">
    <div class="live" id="liveTag"><span class="pip"></span><span id="liveTxt">1ST INNINGS</span></div>
    <div class="tag" id="venueTag"></div>
    <div class="phasechip" id="phaseChip">POWERPLAY</div>
  </div>
  <div class="board">
    <div class="scorecell">
      <div class="batting-team"><span class="teamdot" id="teamDot"></span><b id="batTeam"></b><span>batting</span></div>
      <div class="bigscore">
        <span class="runs" id="scoreTxt">0/0</span>
        <span class="oversbox"><b id="oversTxt">0.0</b> ov · CRR <b id="crrTxt">0.00</b></span>
      </div>
      <div class="chaseline" id="chaseLine"></div>
    </div>
    <div class="players">
      <div class="prow striker"><div class="who"><span class="nm" id="b1n">—</span><span class="role">bat</span></div><div class="fig" id="b1f">0 <span>(0)</span></div></div>
      <div class="prow"><div class="who"><span class="nm" id="b2n">—</span><span class="role">bat</span></div><div class="fig" id="b2f">0 <span>(0)</span></div></div>
      <div class="prow"><div class="who"><span class="nm" id="bwn">—</span><span class="role">bowl</span></div><div class="fig" id="bwf">0.0-0-0-0</div></div>
    </div>
    <div class="overstrip">
      <span class="lbl" id="prevLbl"></span><span class="dots prevover" id="prevDots"></span>
      <span class="lbl" id="thisLbl">Over 1</span><span class="dots" id="thisDots"></span>
    </div>
  </div>
  <div class="mid">
    <div class="wormwrap"><canvas id="worm"></canvas></div>
    <div class="commwrap">
      <div class="commhead">Ball-by-ball</div>
      <div class="comm" id="comm"></div>
    </div>
  </div>
  <div class="flash" id="flash"><div class="fw" id="flashW"></div><div class="fs" id="flashS"></div></div>
  <div class="card" id="card">
    <div class="stamp" id="cardStamp" style="display:none">Simulated</div>
    <div class="k" id="cardK"></div>
    <div class="h" id="cardH"></div>
    <div class="s" id="cardS"></div>
    <button class="primary" id="cardBtn" style="display:none">Replay match</button>
  </div>
  <div class="controls">
    <button class="primary" id="playBtn">Play</button>
    <button class="spd" data-s="1">1x</button>
    <button class="spd on" data-s="2">2x</button>
    <button class="spd" data-s="4">4x</button>
    <button class="spd" data-s="12">12x</button>
    <div class="scrub"><input type="range" id="scrub" min="0" value="0" step="1"><span class="clock" id="clock">0.0 ov</span></div>
    <button id="skipBtn">Skip to result</button>
  </div>
</div>
<script>
const M = __PAYLOAD__;
const LIME="#D6F546", ORG="#FF7A3D", RED="#FF4438", GOLD="#E8C46B",
      INK="#EDEAD9", MUT="#8B9182", DIM="#5A6152";
const TEAMC=[LIME, ORG];

/* deterministic picker */
function pick(arr,seed){let h=(seed*2654435761)>>>0;h^=h>>>13;h=(h*0x5bd1e995)>>>0;h=(h^(h>>>15))>>>0;return arr[h%arr.length];}
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");}

/* ---------- commentary templates ---------- */
const T={
 "0":["No run — {bw} hits a length and {bt} can't get it away.","Dot ball. Tidy from {bw}.","Beaten! {bt} pokes at it and misses.","Pushed straight to the fielder. Nothing there.","{bt} shoulders arms. The pressure builds.","Fizzes past the edge — {bw} is asking questions."],
 "1":["Nudged into the gap, one run.","Quick single — sharp running between the wickets.","Worked off the pads for one.","Soft hands, easy single to rotate the strike.","Dropped into the off side and they scamper through."],
 "2":["Placed wide of the fielder, they come back for two.","Good running — a couple more to the total.","Clipped through midwicket for a brace.","Two more, smartly run."],
 "3":["Driven deep into the outfield — three runs!","Excellent placement, they run three."],
 "4":["FOUR! {bt} threads the gap and it races away.","Crunched through the covers — no chance for the chase.","Short and punished. {bt} rocks back and pulls it to the rope.","Streaky — but four is four off the edge.","Glorious timing from {bt}. That never looked like being stopped.","Full and flicked away fine — four more."],
 "6":["SIX! {bt} launches {bw} deep over the ropes.","That is enormous. Clean off the middle of the bat.","Picked up the length early and deposited it into the stands.","SIX! Flat and brutal over midwicket.","{bt} dances down and goes long — all the way!"],
 "W":["GONE! {dt}.","Big wicket — {dt}.","The breakthrough arrives. {dt}.","That's the end of {bt}. {dt}.","Timber-time drama — {dt}."],
 "WD":["Sprayed down leg — wide called.","Loses his line, that's a wide.","Wide. The extras column ticks over."],
 "NB":["No-ball! Overstepping — a free hit is coming.","He's gone over the line. No-ball, free hit to follow."],
 "LB":["Off the pads and away — leg byes.","They steal a leg bye."],
 "B":["Through everyone! Byes signalled.","The keeper can't gather — byes."]
};
const PRESS=["{need} needed from {bleft} balls.","The equation: {need} off {bleft}.","{need} required, {bleft} deliveries left."];

/* ---------- precompute per-innings snapshots ---------- */
function isLegal(b){return b.out!=="WD"&&b.out!=="NB";}
function fmtOv(balls){return Math.floor(balls/6)+"."+(balls%6);}
function dotLabel(b){
  if(b.w) return {t:"W",c:"rw"};
  if(b.out==="WD") return {t:b.r>1?"wd+"+(b.r-1):"wd",c:"rx"};
  if(b.out==="NB") return {t:"nb"+(b.br?"+"+b.br:""),c:"rx"};
  if(b.out==="LB") return {t:"lb"+b.r,c:"rx"};
  if(b.out==="B") return {t:"b"+b.r,c:"rx"};
  if(b.br===4) return {t:"4",c:"r4"};
  if(b.br===6) return {t:"6",c:"r6"};
  return {t:String(b.r),c:b.r===0?"r0":"r1"};
}
function buildInnings(inn, innIdx, target, offset){
  const order = inn.order.length ? inn.order : [...new Set(inn.balls.map(b=>b.bt))];
  const bat={}, bowl={};
  order.forEach(p=>bat[p]={r:0,b:0});
  let pair=[order[0],order[1]], nextIdx=2;
  const snaps=[];
  let overDots=[], prevDots=[], prevOverNo=0, teamMile=50;
  const fifties=new Set();
  inn.balls.forEach((b,i)=>{
    if(!bat[b.bt]) bat[b.bt]={r:0,b:0};
    if(!bowl[b.bw]) bowl[b.bw]={b:0,r:0,w:0};
    const legal=isLegal(b);
    bat[b.bt].r+=b.br;
    if(legal){bat[b.bt].b++; bowl[b.bw].b++;}
    if(b.et!=="byes"&&b.et!=="legbyes") bowl[b.bw].r+=b.r; else if(b.out==="NB") bowl[b.bw].r+=1;
    let bowlerCredit=b.w && b.dk && b.dk!=="run out";
    if(bowlerCredit) bowl[b.bw].w++;
    const seed=offset+i;
    /* commentary */
    let key=b.w?"W":(b.out in T?b.out:String(Math.min(b.r,4)));
    if(!b.w&&(b.out==="4"||b.out==="6"||b.out==="0"||b.out==="1"||b.out==="2"||b.out==="3")) key=b.out;
    let line=pick(T[key]||T["1"],seed)
      .replace(/{bt}/g,b.bt).replace(/{bw}/g,b.bw).replace(/{dt}/g,b.dt||"he has to go");
    const extras=[];
    /* milestones */
    if(bat[b.bt].r>=50&&!fifties.has(b.bt)&&b.br>0){fifties.add(b.bt);extras.push({cls:"mile",txt:"Fifty for "+b.bt+" — "+bat[b.bt].r+" off "+bat[b.bt].b+"."});}
    if(b.s>=teamMile){extras.push({cls:"mile",txt:teamMile+" up for "+inn.team+"."});teamMile+=50;}
    /* balls bowled so far */
    const ballsBowled = snaps.length? snaps[snaps.length-1].bb + (legal?1:0) : (legal?1:0);
    /* chase pressure note */
    if(innIdx===1&&legal&&ballsBowled%12===0&&b.s<target){
      extras.push({cls:"",txt:pick(PRESS,seed).replace("{need}",target-b.s).replace("{bleft}",120-ballsBowled)});
    }
    /* wicket handling for pair */
    if(b.w){
      const rep=nextIdx<order.length?order[nextIdx++]:null;
      pair=pair.map(p=>p===b.bt?rep:p);
    }
    /* over transitions */
    if(b.o!==prevOverNo){prevDots=overDots;overDots=[];prevOverNo=b.o;}
    overDots=[...overDots, dotLabel(b)];
    /* end-of-over summary */
    let overEnd=null;
    if(legal&&b.lb===6){
      const f=bowl[b.bw];
      overEnd={cls:"",txt:"End of over "+(b.o+1)+" — "+inn.team+" "+b.s+"/"+b.wk+".  "+b.bw+" "+fmtOv(f.b)+"-"+f.r+"-"+f.w+"."};
    }
    /* striker/non-striker (facing batter listed first) */
    const other=pair.find(p=>p&&p!==b.bt)||null;
    snaps.push({
      inn:innIdx, team:inn.team, s:b.s, wk:b.wk, bb:ballsBowled,
      o:b.o, lb:b.lb, ph:b.ph, ball:b,
      b1:b.bt, b1f:bat[b.bt]?{...bat[b.bt]}:null,
      b2:other, b2f:other&&bat[other]?{...bat[other]}:null,
      bw:b.bw, bwf:{...bowl[b.bw]},
      dots:[...overDots], prev:[...prevDots], prevNo:b.o,
      comm:{cls:b.w?"wkt":(b.br===6?"six":(b.br===4?"four":"")),txt:line,label:b.o+"."+(legal?b.lb:b.lb+1)},
      extras:[...extras, ...(overEnd?[overEnd]:[])]
    });
  });
  return snaps;
}

/* ---------- timeline ---------- */
const target=M.target;
const snapA=buildInnings(M.innings[0],0,null,0);
const snapB=buildInnings(M.innings[1],1,target,snapA.length);
const timeline=[];
snapA.forEach((s,i)=>timeline.push({k:"ball",s}));
timeline.push({k:"break"});
snapB.forEach((s,i)=>timeline.push({k:"ball",s}));
timeline.push({k:"result"});
const LAST=timeline.length-1;

/* ---------- element handles ---------- */
const $=id=>document.getElementById(id);
const el={live:$("liveTxt"),liveTag:$("liveTag"),venue:$("venueTag"),phase:$("phaseChip"),dot:$("teamDot"),
  team:$("batTeam"),score:$("scoreTxt"),overs:$("oversTxt"),crr:$("crrTxt"),chase:$("chaseLine"),
  b1n:$("b1n"),b1f:$("b1f"),b2n:$("b2n"),b2f:$("b2f"),bwn:$("bwn"),bwf:$("bwf"),
  prevL:$("prevLbl"),prevD:$("prevDots"),thisL:$("thisLbl"),thisD:$("thisDots"),
  comm:$("comm"),flash:$("flash"),flashW:$("flashW"),flashS:$("flashS"),
  card:$("card"),cardK:$("cardK"),cardH:$("cardH"),cardS:$("cardS"),cardBtn:$("cardBtn"),cardStamp:$("cardStamp"),
  play:$("playBtn"),scrub:$("scrub"),clock:$("clock"),skip:$("skipBtn"),stage:$("stage")};
el.venue.textContent=M.venue.toUpperCase();
el.scrub.max=LAST;

/* ---------- worm chart ---------- */
const canvas=$("worm"),ctx=canvas.getContext("2d");
function wormPoints(snaps){
  const pts=[[0,0]];
  snaps.forEach(s=>{if(isLegal(s.ball)||true){pts.push([s.bb+ (isLegal(s.ball)?0:0.001), s.s, s.ball.w]);}});
  return pts;
}
const ptsA=wormPoints(snapA), ptsB=wormPoints(snapB);
const maxRuns=Math.max(M.innings[0].runs,M.innings[1].runs,target)*1.12+10;
function drawWorm(cursor){
  const dpr=window.devicePixelRatio||1;
  const w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==w*dpr){canvas.width=w*dpr;canvas.height=h*dpr;}
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,w,h);
  const padL=40,padR=14,padT=18,padB=26;
  const X=b=>padL+(b/120)*(w-padL-padR);
  const Y=r=>h-padB-(r/maxRuns)*(h-padT-padB);
  /* grid */
  ctx.strokeStyle="rgba(237,234,217,0.07)";ctx.lineWidth=1;ctx.setLineDash([]);
  ctx.font="500 9px 'IBM Plex Mono',monospace";ctx.fillStyle=DIM;ctx.textAlign="center";
  for(let ov=0;ov<=20;ov+=5){const x=X(ov*6);ctx.beginPath();ctx.moveTo(x,padT);ctx.lineTo(x,h-padB);ctx.stroke();ctx.fillText(ov+" OV",x,h-9);}
  ctx.textAlign="right";
  for(let r=50;r<maxRuns;r+=50){const y=Y(r);ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(w-padR,y);ctx.stroke();ctx.fillText(String(r),padL-6,y+3);}
  /* phase bands */
  ctx.fillStyle="rgba(237,234,217,0.025)";
  ctx.fillRect(X(0),padT,X(36)-X(0),h-padT-padB);
  ctx.fillRect(X(90),padT,X(120)-X(90),h-padT-padB);
  /* how far has the cursor advanced in each innings */
  let na=0,nb=0,mode=0;
  const item=timeline[cursor];
  if(item.k==="ball"){ if(item.s.inn===0){na=snapA.indexOf(item.s)+1;} else {na=snapA.length;nb=snapB.indexOf(item.s)+1;mode=1;} }
  else if(item.k==="break"){na=snapA.length;}
  else {na=snapA.length;nb=snapB.length;mode=1;}
  /* target line in chase */
  if(mode===1){
    ctx.strokeStyle="rgba(232,196,107,0.65)";ctx.setLineDash([5,5]);ctx.beginPath();
    ctx.moveTo(padL,Y(target));ctx.lineTo(w-padR,Y(target));ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=GOLD;ctx.textAlign="left";ctx.fillText("TARGET "+target,padL+4,Y(target)-5);
  }
  function line(pts,n,snaps,color,ghost){
    if(n<=0)return;
    ctx.strokeStyle=ghost?color+"55":color;ctx.lineWidth=ghost?1.6:2.4;ctx.beginPath();
    ctx.moveTo(X(0),Y(0));
    for(let i=0;i<n;i++){const s=snaps[i];ctx.lineTo(X(s.bb),Y(s.s));}
    ctx.stroke();
    /* wickets */
    for(let i=0;i<n;i++){const s=snaps[i];if(s.ball.w){
      ctx.fillStyle=RED;ctx.beginPath();ctx.arc(X(s.bb),Y(s.s),ghost?2.4:3.4,0,7);ctx.fill();}}
    /* head */
    if(!ghost&&n>0){const s=snaps[n-1];ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(s.bb),Y(s.s),4.5,0,7);ctx.fill();}
  }
  line(ptsA,na,snapA,TEAMC[0],mode===1);
  if(mode===1) line(ptsB,nb,snapB,TEAMC[1],false);
  /* legend */
  ctx.textAlign="left";ctx.font="600 9px 'IBM Plex Mono',monospace";
  ctx.fillStyle=TEAMC[0];ctx.fillRect(padL,6,8,8);ctx.fillStyle=MUT;ctx.fillText(M.innings[0].team.toUpperCase(),padL+12,13);
  const w1=ctx.measureText(M.innings[0].team.toUpperCase()).width;
  ctx.fillStyle=TEAMC[1];ctx.fillRect(padL+24+w1,6,8,8);ctx.fillStyle=MUT;ctx.fillText(M.innings[1].team.toUpperCase(),padL+36+w1,13);
}

/* ---------- render ---------- */
let commKeys=new Set();
function renderDots(container,dots,now){
  container.innerHTML="";
  dots.forEach((d,i)=>{
    const sp=document.createElement("span");
    sp.className="dot "+d.c+(now&&i===dots.length-1?" now":"");
    sp.textContent=d.t;container.appendChild(sp);
  });
}
function rebuildComm(cursor){
  el.comm.innerHTML="";commKeys=new Set();
  const items=[];
  for(let i=0;i<=cursor;i++){const t=timeline[i];
    if(t.k==="ball"){items.push({cls:t.s.comm.cls,label:t.s.comm.label,txt:t.s.comm.txt});
      t.s.extras.forEach(e=>items.push({cls:e.cls,label:"",txt:e.txt}));}
    if(t.k==="break") items.push({cls:"mile",label:"",txt:"Innings break. "+M.innings[1].team+" need "+target+" to win."});
  }
  items.slice(-40).forEach(it=>appendComm(it,false));
}
function appendComm(it,animate){
  const d=document.createElement("div");
  d.className="centry "+it.cls+((it.cls==="wkt"||it.cls==="six"||it.cls==="four")?" big":"");
  d.innerHTML=(it.label?'<span class="cb">'+it.label+"</span>":"")+'<span class="ct">'+esc(it.txt)+"</span>";
  if(!animate)d.style.animation="none";
  el.comm.prepend(d);
  while(el.comm.children.length>48)el.comm.removeChild(el.comm.lastChild);
}
function showFlash(kind,sub){
  el.flash.className="flash show"+(kind==="OUT"?" wkt":"");
  el.flashW.textContent=kind;el.flashS.textContent=sub;
  void el.flash.offsetWidth;
  clearTimeout(showFlash._t);showFlash._t=setTimeout(()=>{el.flash.className="flash";},850);
}
function hideCard(){el.card.className="card";}
function showCard(k,h,s,final){
  el.cardK.textContent=k;el.cardH.innerHTML=h;el.cardS.innerHTML=s;
  el.cardBtn.style.display=final?"":"none";
  el.cardStamp.style.display=final?"":"none";
  el.card.className="card show";
}
function render(cursor,animate){
  const item=timeline[cursor];
  el.scrub.value=cursor;
  hideCard();
  if(item.k==="break"){
    const i1=M.innings[0];
    renderBoard(snapA[snapA.length-1],false);
    drawWorm(cursor);
    showCard("Innings break",
      esc(i1.team.toUpperCase())+" "+i1.runs+"/"+i1.wickets,
      "("+i1.overs+" overs — "+esc(i1.endReason)+")<br><b>"+esc(M.innings[1].team)+"</b> need <b>"+target+"</b> from 120 balls.",false);
    el.live.textContent="INNINGS BREAK";el.clock.textContent="—";
    return;
  }
  if(item.k==="result"){
    renderBoard(snapB[snapB.length-1],false);
    drawWorm(cursor);
    const i1=M.innings[0],i2=M.innings[1];
    showCard("Result — "+M.venue,
      '<span class="win">'+esc(M.winner.toUpperCase())+"</span><br>WIN "+esc(M.margin.toUpperCase()),
      esc(i1.team)+" <b>"+i1.runs+"/"+i1.wickets+"</b> ("+i1.overs+")  ·  "+esc(i2.team)+" <b>"+i2.runs+"/"+i2.wickets+"</b> ("+i2.overs+")",true);
    el.liveTag.className="live done";el.live.textContent="MATCH COMPLETE";
    el.clock.textContent="END";
    stop();
    return;
  }
  const s=item.s;
  renderBoard(s,animate);
  el.clock.textContent=fmtOv(s.bb)+" ov · inns "+(s.inn+1);
  drawWorm(cursor);
  if(animate){
    appendComm({cls:s.comm.cls,label:s.comm.label,txt:s.comm.txt},true);
    s.extras.forEach(e=>appendComm({cls:e.cls,label:"",txt:e.txt},true));
    if(s.ball.w) showFlash("OUT",s.ball.dt||s.b1+" departs");
    else if(s.ball.br===6) showFlash("SIX",s.b1+" goes big");
    else if(s.ball.br===4) showFlash("FOUR",s.b1+" finds the rope");
  }
}
function renderBoard(s,animate){
  el.liveTag.className="live";
  el.live.textContent=(s.inn===0?"1ST":"2ND")+" INNINGS";
  el.phase.textContent=s.ph.toUpperCase();
  el.phase.className="phasechip "+s.ph;
  el.dot.style.background=TEAMC[s.inn];
  el.team.textContent=s.team.toUpperCase();
  el.score.textContent=s.s+"/"+s.wk;
  el.overs.textContent=fmtOv(s.bb);
  el.crr.textContent=s.bb?(s.s/(s.bb/6)).toFixed(2):"0.00";
  if(s.inn===1){
    const need=target-s.s,bleft=120-s.bb;
    if(need<=0) el.chase.innerHTML='<span class="ok">Target chased down.</span>';
    else if(bleft<=0||s.wk>=10) el.chase.innerHTML="<b>Fell "+need+" short.</b>";
    else el.chase.innerHTML="Need <b>"+need+"</b> off <b>"+bleft+"</b> · RRR <b>"+(need/(bleft/6)).toFixed(2)+"</b>";
  } else el.chase.innerHTML="First innings · setting the total";
  /* players */
  el.b1n.textContent=s.b1;el.b1f.innerHTML=s.b1f?s.b1f.r+" <span>("+s.b1f.b+")</span>":"—";
  el.b2n.textContent=s.b2||"—";el.b2f.innerHTML=s.b2f?s.b2f.r+" <span>("+s.b2f.b+")</span>":"—";
  el.bwn.textContent=s.bw;
  el.bwf.textContent=fmtOv(s.bwf.b)+"-"+s.bwf.r+"-"+s.bwf.w;
  /* over strips */
  el.thisL.textContent="Over "+(s.o+1);
  renderDots(el.thisD,s.dots,animate);
  el.prevL.textContent=s.prevNo>0?"Over "+s.prevNo:"";
  renderDots(el.prevD,s.prev,false);
}

/* ---------- playback ---------- */
let cursor=0,playing=false,speed=2,timer=null;
function delayFor(item){
  if(item.k==="break")return 2600;
  if(item.k==="result")return 0;
  const b=item.s.ball;
  let d=900;
  if(b.w)d=2000;else if(b.br===6)d=1650;else if(b.br===4)d=1450;
  return d/speed;
}
function step(){
  if(cursor>=LAST){stop();return;}
  cursor++;
  render(cursor,true);
  if(playing&&cursor<LAST) timer=setTimeout(step,delayFor(timeline[cursor]));
  else if(cursor>=LAST) stop();
}
function play(){
  if(cursor>=LAST){cursor=0;rebuildComm(0);}
  playing=true;el.play.textContent="Pause";
  timer=setTimeout(step,220);
}
function stop(){playing=false;el.play.textContent=cursor>=LAST?"Replay":"Play";clearTimeout(timer);}
el.play.onclick=()=>{playing?stop():play();};
el.cardBtn.onclick=()=>{cursor=0;rebuildComm(0);render(0,false);play();};
el.skip.onclick=()=>{stop();cursor=LAST;rebuildComm(cursor);render(cursor,false);};
document.querySelectorAll(".spd").forEach(b=>{b.onclick=()=>{
  speed=Number(b.dataset.s);
  document.querySelectorAll(".spd").forEach(x=>x.classList.toggle("on",x===b));
};});
el.scrub.oninput=e=>{stop();cursor=Number(e.target.value);rebuildComm(cursor);render(cursor,false);};
window.addEventListener("resize",()=>drawWorm(cursor));
document.addEventListener("keydown",e=>{if(e.code==="Space"){e.preventDefault();playing?stop():play();}});
/* test hook */
window.__seek=(i,anim)=>{stop();cursor=Math.min(LAST,i);rebuildComm(cursor);render(cursor,!!anim);};
window.__play=play; window.__total=LAST;

render(0,false);
rebuildComm(0);
</script>
</body>
</html>
"""
