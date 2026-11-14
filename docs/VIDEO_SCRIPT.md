# DRAFT — rewrite in your own words

**Hard limit: 30 seconds** (Space Apps 2026 guide). English, or another language with English subtitles.
No people under 18 on screen. Any AI-generated image/video needs a visible watermark (we plan none).
Screen recording of `web/index.html` only. **No board footage** (no board access, D-23); say
"same C code on the ground computer and in the browser", never "on the board".

| Time | Picture | Voice (≈ 2.5 words/s) |
|---|---|---|
| 0:00–0:03 | Team name + CrewWatch title | "We're <team>, from Ankara. This is CrewWatch." |
| 0:03–0:08 | "Why on board?" box, Mars, 25 min | "On Mars, a question to Earth takes up to forty-four minutes round trip. Health alerts must come from the ship." |
| 0:08–0:18 | Panel, Crew A, press Next fault + Play at 10×; stop before onset + 120 s (the range strip lights at +133 s for an unrelated reason: don't show that as part of this fault) | "Here a heart-rate sensor freezes. Every value is still in range, so a limit check does not notice. CrewWatch flags it within ten seconds (8 s in this replay) and tells the astronaut what to check." |
| 0:18–0:25 | Results card | "We tested it honestly on real recordings: it catches frozen and silent sensors, with eight times fewer false alarms on new people. Slow drift is still unsolved, and we say so." |
| 0:25–0:30 | Title + "integer · deterministic · flight code" | "Integer-only flight code, the same decision on every computer. CrewWatch." |

Check before upload: length ≤ 0:30, link public, subtitles if not in English.

Optional honest beat if you switch to slides: Crew D at 1:30:00, bradycardia. Here the range check
alarms at +50 s and CrewWatch never does. That is the "two layers" point.
