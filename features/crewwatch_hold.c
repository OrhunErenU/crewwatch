/************************************************************************
 * CREWWATCH -- HOLD transform
 *
 * Written during NASA Space Apps 2026 (48 h).
 * Licensed under the Apache License, Version 2.0
 ************************************************************************/

#include <stddef.h>

#include "crewwatch_hold.h"

void CREWWATCH_HoldInit(CREWWATCH_HoldState_t *State)
{
    if (State == NULL)
    {
        return;
    }

    State->PrevRaw   = 0u;
    State->HoldTicks = 0u;
    State->HasPrev   = false;
}

void CREWWATCH_HoldAdvance(CREWWATCH_HoldState_t *State, uint32_t Raw)
{
    if (State == NULL)
    {
        return;
    }

    if (State->HasPrev && (Raw == State->PrevRaw))
    {
        /* saturate instead of wrapping: a wrap to 0 would look like
         * "value just changed" exactly when the sensor has been frozen
         * longest -- the worst possible moment to go quiet. */
        if (State->HoldTicks < CREWWATCH_HOLD_MAX)
        {
            State->HoldTicks++;
        }
    }
    else
    {
        State->HoldTicks = 0u;
    }

    State->PrevRaw = Raw;
    State->HasPrev = true;
}

bool CREWWATCH_ApplyHold(const TLM_WATCH_FeatureDef_t *Def, const CREWWATCH_HoldState_t *State, int16_t *Out)
{
    TLM_WATCH_FeatureDef_t AsAge;
    TLM_WATCH_FeatState_t  Unused;

    if ((Def == NULL) || (State == NULL) || (Out == NULL))
    {
        return false;
    }

    if (!State->HasPrev)
    {
        return false;
    }

    /* Copy the definition and route it through the existing AGE scaling.
     * AGE ignores Offset/Type and the DIFF state. */
    AsAge           = *Def;
    AsAge.Transform = TLM_WATCH_XFORM_AGE;
    Unused.PrevRaw  = 0u;
    Unused.HasPrev  = false;

    return TLM_WATCH_ApplyTransform(&AsAge, 0u, State->HoldTicks, &Unused, Out);
}
