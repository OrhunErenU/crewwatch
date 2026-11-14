# Space Apps 2026 project page: final text

Copy each block into the field with the same name. Written with AI assistance and disclosed in
`AI_USE.md`. Numbers come from `eval/RESULTS.md`. If the evaluation is re-run, check them again.

---

## Project Name

CrewWatch

## High-Level Project Summary

On the way to Mars, a message to Earth takes up to 22 minutes one way, and some weeks there is no
link at all. If an astronaut's wearable sensor fails, nobody on the ground will notice in time, and a
broken sensor can look perfectly normal. A heart-rate sensor that freezes keeps sending a believable
number. Every value stays inside its limits, so the standard limit check on the spacecraft says
nothing. CrewWatch runs on the spacecraft's own computer. Every second it checks whether each sensor's
value is still moving, whether each sensor is still talking, and whether the readings make sense
together. When it suspects a sensor, it asks the astronaut to check it by hand: a 15-second pulse
count is compared with what the chest strap says, and the astronaut is told which one to trust.
The same panel takes the astronaut's own daily check-in (blood pressure, temperature, blood glucose,
sleep, mood), shows vital signs over time with a color-coded status, radiation exposure, and says in
plain words what to do next and when to bring in the crew medical officer. It is written in integer-only C,
built on flight software we wrote earlier, so the same input always gives the same alert on any
computer. We tested it on real recordings of 15 people and we report where it fails as well as where
it works.

## Link to Project Demo

https://github.com/OrhunErenU/crewwatch/blob/main/docs/crewwatch-demo.mp4

## Link to Final Project

https://github.com/OrhunErenU/crewwatch

## Detailed Project Description

**What it does**

CrewWatch watches five wearable channels: heart rate, heart-rate variability, activity, skin
temperature and skin conductance. Every second it builds nine numbers from them:

- the five levels, each compared with that astronaut's own baseline;
- HOLD: how many seconds heart rate (and HRV) have not changed at all;
- AGE: how many seconds since each sensor last sent data.

A Mahalanobis model, stored as a 162-byte table of 8-bit integers, scores these nine numbers together.
A second copy of the same model scores their 64-second average. When a score crosses its threshold,
CrewWatch shows an alert card, for example:

> Heart rate has read exactly 115.9 bpm for 8 s while data keeps arriving (longest seen in normal
> data: 8 s). Sensor may be frozen: re-seat or restart the chest strap.

Every sentence on the card comes from a number the software measured. CrewWatch never says what is
wrong with the astronaut. It says what to check.

**How it answers the challenge**

The challenge asks for a visual tool that lets astronauts assess their own health and act on it.
CrewWatch's panel (`web/index.html`, works offline) does this for a crew of four:

- color-coded crew cards (green / amber / red) with heart rate and temperature at a glance;
- dynamic charts of every indicator over time, with the alert threshold drawn in;
- an alert card with step-by-step instructions: check the sensor first, then note how you feel and
  log it for the crew medical officer;
- a radiation panel (NASA DONKI solar particle events + measured Mars-transit dose rate), and reference
  panels for bone loss and sleep from published spaceflight studies (not crew data);
- a "why on board?" box showing the light-time delay to Earth (NASA HRP hazard: distance from Earth);
- a **self check-in** for the indicators the challenge names: blood pressure, pulse, oral temperature,
  blood glucose, hours slept and mood (1–5). Each value is classified against a published threshold
  (AHA 2017 blood-pressure categories, CDC fever ≥ 38.0 °C, ADA low glucose < 70 / < 54 mg/dL,
  AASM/SRS ≥ 7 h sleep), shown as a green/amber/red chip, with what to do next. Three low-mood
  check-ins in a row suggest a private talk with the crew medical officer.

Our main addition is the question that comes before every health judgement: *is this reading still
true?* The check-in closes that loop. When CrewWatch suspects the heart-rate sensor, the alert card
asks the astronaut to count their own pulse for 15 seconds. The count is compared with the chest
strap at that moment (agree if within 10 bpm or 10 %). In the demo, Crew A counts 25 beats = 100 bpm
while the frozen strap still reports 116, and CrewWatch answers: trust your own count, re-seat the
strap. The hand count comes from the real recording, not an invented number. The check-in rules are
integer-only C, the same code style and the same WebAssembly module as the monitor. A test checks
that 5,000 check-ins give identical results on the PC and in the browser.

**How we tested it**

We did not simulate healthy people. Normal data comes from PPG-DaLiA, real recordings of 15 people
going through a normal day (stairs, cycling, walking, driving, eating). We trained on 8 people, tuned
thresholds on 3, and kept 4 people aside as our "crew". On top of the crew's real recordings we
injected five kinds of problems and compared three monitors. All three were tuned to the same
false-alarm budget:

| Problem injected | Limit check | Limit check + "unchanged" rule | CrewWatch |
|---|---|---|---|
| Heart-rate sensor frozen | 13 % (chance level) | 100 % | 100 % |
| Chest strap stops sending | 8 % (chance level) | 100 % (median 8 s) | 100 % (median 3 s) |
| Heart rate falls to 35 bpm within a minute | **77 %** | **77 %** | 32 % |
| Heart rate does not follow activity | no better than chance | no better than chance | no better than chance |
| Slow fever-like drift | no better than chance | no better than chance | no better than chance |
| False alarms on the 4 new people | 2.9 % of seconds (104/hour) | 2.9 % (104/hour) | **0.35 % (12.5/hour)** |

What this tells us:

- A limit check cannot see a frozen or silent sensor. We saw the same thing on real flight hardware
  before the hackathon: 316 samples, 0 alarms.
- A simple "value has not changed" rule catches those faults too, and we say so. CrewWatch does the
  same job inside one model, reacts faster to a silent sensor, and raised about 8 times fewer false
  alarms on people it had never seen.
- When one channel clearly leaves its normal range (bradycardia), the plain limit check wins. The two
  should run side by side.
- Slow changes, like a fever building over half an hour, were not caught by any of the three monitors
  with these wrist sensors at one reading per second. We are not hiding that. It is the next problem
  to solve.

**Why integer-only code matters**

The same C code, compiled once for a normal PC and once for a web browser (WebAssembly), produced the
same 67,388 scores bit for bit. The panel checks this again every time it opens. The inference engine
underneath was measured on a flight-class processor without a floating-point unit in earlier work:
bit-exact against the ground computer, and 0.64 % of a one-second time budget. We did not have that
board during the hackathon, so CrewWatch itself was not run on it.

The model is updated on the ground. Only the small table is sent to the spacecraft. Nothing is trained
in orbit.

**What we hope to achieve**

NASA's own plans for Mars move medical decisions from Mission Control to the crew (Earth-Independent
Medical Operations). Decision-support tools for the crew medical officer depend on sensor data that
can be trusted. CrewWatch is a small, checkable layer underneath them. It tells the crew when a
sensor stopped telling the truth.

**Tools**

C (flight inference library `tinyinfer`, cFS feature code), Python (no machine-learning framework,
only the standard library plus numpy for loading the dataset), Emscripten/WebAssembly, plain
HTML/JavaScript for the panel (works offline), WSL Ubuntu with gcc.

**What existed before the hackathon**

The integer inference engine and the cFS feature code were written by a team member during an
internship at TÜBİTAK UZAY (July–August 2026) and are open source. We reused them without changes.
During the hackathon we built the HOLD feature, the wearable data pipeline, the fault injector, the
evaluation, the alert text, the WebAssembly build and the panel. Details: `PRIOR_WORK.md`.

## Use of Super Intelligence (SI)

Yes. We used an AI coding assistant (Claude Code, Anthropic) to write most of the hackathon code, to
draft this page and the video captions, and to check sources. The idea, the plan and the decision to
compare against simple baselines came from the team before the assistant was used. The team ran and
reviewed the results. Every source file written with AI help says so in its header. `AI_USE.md` lists
everything. No images, audio or data were generated by AI. The demo video is a screen recording of
our own software.

## NASA Data

- **DONKI** (NASA Community Coordinated Modeling Center): 214 Solar Energetic Particle events from
  January 2024 to November 2026, shown on the radiation panel.
- **Mars Science Laboratory / RAD** published dose rates (Zeitlin et al. 2013; Hassler et al. 2014)
  for the radiation baseline.
- NASA Human Research Program resources listed for this challenge: "5 Hazards of Human Spaceflight"
  (https://www.nasa.gov/hrp/hazards/). We address "distance from Earth" (on-board alerts, light-time
  box) and "space radiation" (DONKI panel). Our bone and sleep reference panels follow two risks
  listed in "Risks of Human Spaceflight" (https://www.nasa.gov/hrp/risks/): "Risk of Spaceflight-Induced
  Bone Changes" and "Risk of Inadequate Sleep and Irregular Schedules".
- NASA HRP / NTRS documents for the problem framing: EIMO Concept of Operations
  (NTRS 20240001402, 20250000009).

## Space Agency Partner Data and Other References

**Code (all open source, used as-is):**
- `tinyinfer`: integer inference library, https://github.com/OrhunErenU/tinyinfer (Apache-2.0;
  written by a team member before the hackathon).
- `cfs-m2s150`: NASA cFS port and `tlm_watch` app (feature transforms, window mean, ground tools),
  https://github.com/OrhunErenU/cfs-m2s150 (Apache-2.0; written by a team member before the
  hackathon). It builds on NASA core Flight System (cFS), https://github.com/nasa/cFS (Apache-2.0).
- Emscripten 3.1.74 (WebAssembly compiler), https://emscripten.org (MIT / University of Illinois NCSA).
- Python 3 standard library, numpy (BSD) for reading the dataset files, Node.js for one test script.
- AI coding assistant: Claude Code (Anthropic); see the Use of SI field.

**Data and literature:**
- PPG-DaLiA: Reiss, Indlekofer, Schmidt, Van Laerhoven, *Sensors* 19(14):3079, 2019. UCI
  doi:10.24432/C53890, CC BY 4.0. All physiological data.
- Our own board telemetry dataset: doi:10.5281/zenodo.22045173 (CC BY 4.0).
- Karjalainen & Viitasalo 1986 (heart rate rise with fever); Barger et al. 2014 (astronaut sleep);
  Lang et al. 2004 (bone loss); van Hees et al. 2013 (activity metric); Zhang, Liu, Kato 2018
  (wearable sensor faults).
- CSA, "Monitoring Radiation for Astronaut Health" (challenge partner resource), background for the
  radiation panel.
- Full list with every number used: `data/SOURCES.md`.
- No images, music or other copyrighted media are used.
