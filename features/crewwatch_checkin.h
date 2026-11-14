/************************************************************************
 * CREWWATCH -- astronaut self check-in, evaluated by flight-style C
 *
 * Written during NASA Space Apps 2026 (48 h).
 * Written with AI assistance (Claude Code), see AI_USE.md.
 * Licensed under the Apache License, Version 2.0
 ************************************************************************/

/**
 * @file
 *   The astronaut types in what they measured themselves (blood pressure,
 *   a 15-second pulse count, oral temperature, blood glucose, hours slept,
 *   mood 1-5). This module classifies each value against published
 *   thresholds and -- the CrewWatch part -- CROSS-CHECKS THE MANUAL PULSE
 *   AGAINST THE WEARABLE'S HEART RATE. A human measurement becomes the
 *   reference that tells whether the wearable is still telling the truth.
 *
 * Same rules as tlm_watch_feature.c: integer only, no division, no float,
 * no malloc, no cFS headers. It runs unchanged on the ground computer
 * (gcc) and in the browser (wasm32); tests/test_wasm_bitexact.js checks
 * both give identical results.
 *
 * Thresholds and their sources (data/SOURCES.md):
 *   BP   AHA/ACC 2017: normal <120/<80, elevated 120-129/<80,
 *        stage 1 130-139 or 80-89, stage 2 >=140 or >=90,
 *        crisis >180 and/or >120. Higher of the two categories wins.
 *   Temp CDC: fever = measured oral temperature >= 38.0 degC (100.4 F).
 *   Glu  ADA Standards of Care: level 1 < 70 mg/dL, level 2 < 54 mg/dL.
 *   Sleep AASM/SRS 2015 consensus: adults >= 7 h per night.
 *   Mood 1-5 self rating; <= 2 counts as low (assumption; no cut-off
 *        exists, so the tool only reports streaks of low days).
 *   Pulse agreement: |manual - wearable| <= 10 bpm or <= 10 % of the
 *        manual count (assumption: a 15-s count x 4 is quantised to 4 bpm).
 */

#ifndef CREWWATCH_CHECKIN_H
#define CREWWATCH_CHECKIN_H

#include <stdint.h>
#include <stdbool.h>

#define CW_CI_HAS_BP    0x0001u
#define CW_CI_HAS_PULSE 0x0002u
#define CW_CI_HAS_TEMP  0x0004u
#define CW_CI_HAS_GLU   0x0008u
#define CW_CI_HAS_SLEEP 0x0010u
#define CW_CI_HAS_MOOD  0x0020u

/* result codes, 0 = not measured in every field */
enum { CW_BP_NONE = 0, CW_BP_NORMAL, CW_BP_ELEVATED, CW_BP_STAGE1, CW_BP_STAGE2, CW_BP_CRISIS };
enum { CW_TEMP_NONE = 0, CW_TEMP_NORMAL, CW_TEMP_FEVER };
enum { CW_GLU_NONE = 0, CW_GLU_OK, CW_GLU_LOW1, CW_GLU_LOW2 };
enum { CW_SLEEP_NONE = 0, CW_SLEEP_OK, CW_SLEEP_SHORT };
enum { CW_MOOD_NONE = 0, CW_MOOD_OK, CW_MOOD_LOW };
enum { CW_PULSE_NONE = 0, CW_PULSE_AGREE, CW_PULSE_DISAGREE, CW_PULSE_NO_WEARABLE };
enum { CW_OVERALL_GREEN = 0, CW_OVERALL_AMBER, CW_OVERALL_RED };

/** What the astronaut entered. 16 bytes. */
typedef struct
{
    uint16_t Present;     /**< CW_CI_HAS_* bits                     */
    uint16_t SysMmHg;     /**< systolic, mmHg                       */
    uint16_t DiaMmHg;     /**< diastolic, mmHg                      */
    uint16_t PulseBpm;    /**< manual count (15 s x 4), bpm         */
    int16_t  TempX10;     /**< oral temperature, 0.1 degC           */
    uint16_t GlucoseMgDl; /**< blood glucose, mg/dL                 */
    uint16_t SleepMin;    /**< sleep last night, minutes            */
    uint8_t  Mood;        /**< 1 (very low) .. 5 (very good)        */
    uint8_t  Pad;
} CREWWATCH_CheckIn_t;

/** Classification. 12 bytes. */
typedef struct
{
    uint8_t Bp, Temp, Glucose, Sleep, Mood, Pulse;
    int16_t PulseDiffX10; /**< manual - wearable, 0.1 bpm (no division needed) */
    uint8_t Overall;      /**< CW_OVERALL_*                                   */
    uint8_t Pad[3];
} CREWWATCH_CheckInResult_t;

/** Wearable is considered live if its source spoke within this many ticks. */
#define CW_CI_WEARABLE_MAX_AGE 5u

/**
 * \brief Classify one check-in.
 * \param WearableHrX10   latest wearable heart rate, 0.1 bpm (latched value)
 * \param WearableAge     ticks since the chest strap last sent a packet
 * \return false on NULL arguments or out-of-range input (nothing written)
 */
bool CREWWATCH_EvaluateCheckIn(const CREWWATCH_CheckIn_t *In, uint16_t WearableHrX10, uint16_t WearableAge,
                               CREWWATCH_CheckInResult_t *Out);

/** Number of most-recent consecutive mood entries <= 2 (oldest first in Moods). */
uint16_t CREWWATCH_LowMoodStreak(const uint8_t *Moods, uint16_t N);

#endif /* CREWWATCH_CHECKIN_H */
