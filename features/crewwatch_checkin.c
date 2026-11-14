/************************************************************************
 * CREWWATCH -- astronaut self check-in (see crewwatch_checkin.h)
 *
 * Written during NASA Space Apps 2026 (48 h).
 * Written with AI assistance (Claude Code), see AI_USE.md.
 * Licensed under the Apache License, Version 2.0
 ************************************************************************/

#include <stddef.h>

#include "crewwatch_checkin.h"

static uint8_t CW_BpCategory(uint16_t Sys, uint16_t Dia)
{
    uint8_t S, D;

    /* AHA/ACC 2017; the higher of the two categories wins */
    if (Sys > 180u)      { S = CW_BP_CRISIS; }
    else if (Sys >= 140u) { S = CW_BP_STAGE2; }
    else if (Sys >= 130u) { S = CW_BP_STAGE1; }
    else if (Sys >= 120u) { S = CW_BP_ELEVATED; }
    else                  { S = CW_BP_NORMAL; }

    if (Dia > 120u)      { D = CW_BP_CRISIS; }
    else if (Dia >= 90u)  { D = CW_BP_STAGE2; }
    else if (Dia >= 80u)  { D = CW_BP_STAGE1; }
    else                  { D = CW_BP_NORMAL; } /* diastolic has no "elevated" band */

    return (S > D) ? S : D;
}

static int32_t CW_Abs32(int32_t V)
{
    return (V < 0) ? -V : V;
}

bool CREWWATCH_EvaluateCheckIn(const CREWWATCH_CheckIn_t *In, uint16_t WearableHrX10, uint16_t WearableAge,
                               CREWWATCH_CheckInResult_t *Out)
{
    CREWWATCH_CheckInResult_t R;
    int32_t                   Diff;

    if ((In == NULL) || (Out == NULL))
    {
        return false;
    }

    /* plausibility: reject typing errors instead of classifying them */
    if (((In->Present & CW_CI_HAS_BP) != 0u) &&
        ((In->SysMmHg < 50u) || (In->SysMmHg > 300u) || (In->DiaMmHg < 20u) || (In->DiaMmHg > 200u) ||
         (In->DiaMmHg >= In->SysMmHg)))
    {
        return false;
    }
    if (((In->Present & CW_CI_HAS_PULSE) != 0u) && ((In->PulseBpm < 20u) || (In->PulseBpm > 250u)))
    {
        return false;
    }
    if (((In->Present & CW_CI_HAS_TEMP) != 0u) && ((In->TempX10 < 300) || (In->TempX10 > 450)))
    {
        return false;
    }
    if (((In->Present & CW_CI_HAS_GLU) != 0u) && ((In->GlucoseMgDl < 10u) || (In->GlucoseMgDl > 800u)))
    {
        return false;
    }
    if (((In->Present & CW_CI_HAS_SLEEP) != 0u) && (In->SleepMin > 1440u))
    {
        return false;
    }
    if (((In->Present & CW_CI_HAS_MOOD) != 0u) && ((In->Mood < 1u) || (In->Mood > 5u)))
    {
        return false;
    }

    R.Bp = R.Temp = R.Glucose = R.Sleep = R.Mood = R.Pulse = 0u;
    R.PulseDiffX10 = 0;
    R.Overall      = CW_OVERALL_GREEN;
    R.Pad[0] = R.Pad[1] = R.Pad[2] = 0u;

    if ((In->Present & CW_CI_HAS_BP) != 0u)
    {
        R.Bp = CW_BpCategory(In->SysMmHg, In->DiaMmHg);
    }
    if ((In->Present & CW_CI_HAS_TEMP) != 0u)
    {
        R.Temp = (In->TempX10 >= 380) ? CW_TEMP_FEVER : CW_TEMP_NORMAL;
    }
    if ((In->Present & CW_CI_HAS_GLU) != 0u)
    {
        R.Glucose = (In->GlucoseMgDl < 54u) ? CW_GLU_LOW2 : (In->GlucoseMgDl < 70u) ? CW_GLU_LOW1 : CW_GLU_OK;
    }
    if ((In->Present & CW_CI_HAS_SLEEP) != 0u)
    {
        R.Sleep = (In->SleepMin < 420u) ? CW_SLEEP_SHORT : CW_SLEEP_OK;
    }
    if ((In->Present & CW_CI_HAS_MOOD) != 0u)
    {
        R.Mood = (In->Mood <= 2u) ? CW_MOOD_LOW : CW_MOOD_OK;
    }

    if ((In->Present & CW_CI_HAS_PULSE) != 0u)
    {
        if ((WearableAge > CW_CI_WEARABLE_MAX_AGE) || (WearableHrX10 == 0u))
        {
            R.Pulse = CW_PULSE_NO_WEARABLE;
        }
        else
        {
            /* everything in 0.1 bpm so no division is needed:
             * agree if |diff| <= 10 bpm (100) or <= 10 % of the manual count
             * (|diff| * 10 <= manual * 10 * 10 / 10  ->  |diffX10| <= manual) */
            Diff           = (int32_t)In->PulseBpm * 10 - (int32_t)WearableHrX10;
            R.PulseDiffX10 = (int16_t)Diff; /* |Diff| <= 2500 + 65535: clamp below */
            if (Diff > 32767)
            {
                R.PulseDiffX10 = 32767;
            }
            else if (Diff < -32768)
            {
                R.PulseDiffX10 = -32768;
            }
            R.Pulse = ((CW_Abs32(Diff) <= 100) || (CW_Abs32(Diff) <= (int32_t)In->PulseBpm)) ? CW_PULSE_AGREE
                                                                                             : CW_PULSE_DISAGREE;
        }
    }

    /* overall colour (assumption: red = act now per the cited guideline,
     * amber = re-check / tell the crew medical officer at the next contact) */
    if ((R.Bp == CW_BP_CRISIS) || (R.Glucose == CW_GLU_LOW2))
    {
        R.Overall = CW_OVERALL_RED;
    }
    else if ((R.Bp >= CW_BP_STAGE1) || (R.Temp == CW_TEMP_FEVER) || (R.Glucose == CW_GLU_LOW1) ||
             (R.Sleep == CW_SLEEP_SHORT) || (R.Mood == CW_MOOD_LOW) || (R.Pulse == CW_PULSE_DISAGREE))
    {
        R.Overall = CW_OVERALL_AMBER;
    }

    *Out = R;
    return true;
}

uint16_t CREWWATCH_LowMoodStreak(const uint8_t *Moods, uint16_t N)
{
    uint16_t Count = 0u;

    if (Moods == NULL)
    {
        return 0u;
    }
    while ((Count < N) && (Moods[N - 1u - Count] >= 1u) && (Moods[N - 1u - Count] <= 2u))
    {
        Count++;
    }
    return Count;
}
