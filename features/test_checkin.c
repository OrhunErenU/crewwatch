/************************************************************************
 * Host test for crewwatch_checkin.c -- build: features/build_host.sh
 * Written with AI assistance (Claude Code), see AI_USE.md.
 ************************************************************************/

#include <stdio.h>
#include <string.h>

#include "crewwatch_checkin.h"

static int Fails = 0, Checks = 0;
#define CHECK(c, m) do { Checks++; if (!(c)) { Fails++; printf("  FAIL  %s (line %d)\n", m, __LINE__); } } while (0)

static CREWWATCH_CheckIn_t Bp(uint16_t S, uint16_t D)
{
    CREWWATCH_CheckIn_t c;
    memset(&c, 0, sizeof(c));
    c.Present = CW_CI_HAS_BP;
    c.SysMmHg = S;
    c.DiaMmHg = D;
    return c;
}

static uint8_t BpCat(uint16_t S, uint16_t D)
{
    CREWWATCH_CheckIn_t       c = Bp(S, D);
    CREWWATCH_CheckInResult_t r;
    if (!CREWWATCH_EvaluateCheckIn(&c, 0, 0xFFFF, &r)) return 255;
    return r.Bp;
}

int main(void)
{
    CREWWATCH_CheckIn_t       c;
    CREWWATCH_CheckInResult_t r;
    uint8_t                   moods[6] = {4, 2, 3, 1, 2, 2};

    CHECK(sizeof(CREWWATCH_CheckIn_t) == 16, "check-in struct is 16 bytes");
    CHECK(sizeof(CREWWATCH_CheckInResult_t) == 12, "result struct is 12 bytes");

    /* AHA/ACC 2017 boundaries */
    CHECK(BpCat(119, 79) == CW_BP_NORMAL, "119/79 normal");
    CHECK(BpCat(120, 79) == CW_BP_ELEVATED, "120/79 elevated");
    CHECK(BpCat(129, 79) == CW_BP_ELEVATED, "129/79 elevated");
    CHECK(BpCat(125, 80) == CW_BP_STAGE1, "125/80 stage 1 (diastolic decides)");
    CHECK(BpCat(130, 70) == CW_BP_STAGE1, "130/70 stage 1");
    CHECK(BpCat(139, 89) == CW_BP_STAGE1, "139/89 stage 1");
    CHECK(BpCat(140, 70) == CW_BP_STAGE2, "140/70 stage 2");
    CHECK(BpCat(118, 90) == CW_BP_STAGE2, "118/90 stage 2 (diastolic)");
    CHECK(BpCat(180, 110) == CW_BP_STAGE2, "180/110 stage 2 (crisis is > 180)");
    CHECK(BpCat(181, 100) == CW_BP_CRISIS, "181/100 crisis");
    CHECK(BpCat(170, 121) == CW_BP_CRISIS, "170/121 crisis (diastolic)");
    CHECK(BpCat(120, 130) == 255, "dia >= sys rejected as typing error");
    CHECK(BpCat(40, 30) == 255, "implausible BP rejected");

    /* temperature (CDC, >= 38.0) */
    memset(&c, 0, sizeof(c));
    c.Present = CW_CI_HAS_TEMP;
    c.TempX10 = 379;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Temp == CW_TEMP_NORMAL && r.Overall == CW_OVERALL_GREEN, "37.9 normal");
    c.TempX10 = 380;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Temp == CW_TEMP_FEVER && r.Overall == CW_OVERALL_AMBER, "38.0 fever, amber");

    /* glucose (ADA) */
    memset(&c, 0, sizeof(c));
    c.Present     = CW_CI_HAS_GLU;
    c.GlucoseMgDl = 70;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Glucose == CW_GLU_OK, "70 ok");
    c.GlucoseMgDl = 69;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Glucose == CW_GLU_LOW1 && r.Overall == CW_OVERALL_AMBER, "69 level 1");
    c.GlucoseMgDl = 53;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Glucose == CW_GLU_LOW2 && r.Overall == CW_OVERALL_RED, "53 level 2, red");

    /* sleep (AASM/SRS >= 7 h) and mood */
    memset(&c, 0, sizeof(c));
    c.Present  = CW_CI_HAS_SLEEP | CW_CI_HAS_MOOD;
    c.SleepMin = 420;
    c.Mood     = 3;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Sleep == CW_SLEEP_OK && r.Mood == CW_MOOD_OK, "7 h, mood 3 ok");
    c.SleepMin = 365;
    c.Mood     = 2;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Sleep == CW_SLEEP_SHORT && r.Mood == CW_MOOD_LOW, "6 h 5 min short, mood 2 low");
    c.Mood = 6;
    CHECK(!CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r), "mood 6 rejected");

    /* pulse cross-check against the wearable (the CrewWatch part) */
    memset(&c, 0, sizeof(c));
    c.Present  = CW_CI_HAS_PULSE;
    c.PulseBpm = 72;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 712, 0, &r) && r.Pulse == CW_PULSE_AGREE && r.PulseDiffX10 == 8, "72 vs 71.2 agree, diff +0.8");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 820, 0, &r) && r.Pulse == CW_PULSE_AGREE, "72 vs 82.0: 10.0 bpm, still agree");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 821, 0, &r) && r.Pulse == CW_PULSE_DISAGREE && r.Overall == CW_OVERALL_AMBER, "72 vs 82.1 disagree");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 1159, 2, &r) && r.Pulse == CW_PULSE_DISAGREE && r.PulseDiffX10 == -439, "frozen 115.9 vs 72: disagree, -43.9");
    c.PulseBpm = 150;
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 1350, 0, &r) && r.Pulse == CW_PULSE_AGREE, "150 vs 135: 10 % rule -> agree");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 1349, 0, &r) && r.Pulse == CW_PULSE_DISAGREE, "150 vs 134.9: just outside 10 %");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 1500, 6, &r) && r.Pulse == CW_PULSE_NO_WEARABLE, "strap silent > 5 s -> no wearable");
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 0, 0, &r) && r.Pulse == CW_PULSE_NO_WEARABLE, "no HR yet -> no wearable");

    /* combined, nothing present */
    memset(&c, 0, sizeof(c));
    CHECK(CREWWATCH_EvaluateCheckIn(&c, 700, 0, &r) && r.Overall == CW_OVERALL_GREEN && r.Pulse == CW_PULSE_NONE, "empty check-in green");
    CHECK(!CREWWATCH_EvaluateCheckIn(NULL, 0, 0, &r) && !CREWWATCH_EvaluateCheckIn(&c, 0, 0, NULL), "NULL safety");

    /* low-mood streak */
    CHECK(CREWWATCH_LowMoodStreak(moods, 6) == 3, "streak of 3 low days at the end");
    CHECK(CREWWATCH_LowMoodStreak(moods, 3) == 0, "ends on 3 -> 0");
    CHECK(CREWWATCH_LowMoodStreak(NULL, 3) == 0, "NULL -> 0");

    printf("crewwatch_checkin: %d/%d checks passed\n", Checks - Fails, Checks);
    return Fails == 0 ? 0 : 1;
}
