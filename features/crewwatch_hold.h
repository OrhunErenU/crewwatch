/************************************************************************
 * CREWWATCH -- HOLD transform (ticks since a channel's value last changed)
 *
 * Written during NASA Space Apps 2026 (48 h). Same rules as
 * tlm_watch_feature.c: no float, no division, no malloc, no cFS headers.
 *
 * Licensed under the Apache License, Version 2.0
 ************************************************************************/

/**
 * @file
 *   HOLD = how many ticks the latched raw value of one channel has stayed
 *   bit-for-bit identical.
 *
 * Why it is not AGE
 *   AGE counts ticks since the SOURCE last delivered a packet. A frozen
 *   sensor keeps delivering packets (AGE = 0) that carry the same value
 *   forever. AGE cannot see that; HOLD can. A silent source shows up in
 *   both (the latch keeps the last value, so HOLD grows too).
 *
 * Why only a counter lives here
 *   Scaling ((V - Bias) * Scale) >> Shift with int16 saturation already
 *   exists in tlm_watch_feature.c for AGE. HOLD reuses that exact code
 *   path: CREWWATCH_ApplyHold() hands the counter to
 *   TLM_WATCH_ApplyTransform() as if it were an age. No arithmetic is
 *   written twice.
 */

#ifndef CREWWATCH_HOLD_H
#define CREWWATCH_HOLD_H

#include <stdint.h>
#include <stdbool.h>

#include "tlm_watch_feature.h"

/** Saturation value of the counter (same ceiling the latch uses for AGE). */
#define CREWWATCH_HOLD_MAX ((uint16_t)0xFFFFu)

/**
 * \brief Per-channel state carried between ticks.
 */
typedef struct
{
    uint32_t PrevRaw;   /**< \brief raw value seen at the previous tick       */
    uint16_t HoldTicks; /**< \brief ticks the value has not changed           */
    bool     HasPrev;   /**< \brief PrevRaw is meaningful                      */
} CREWWATCH_HoldState_t;

/**
 * \brief Reset to "never seen". The first tick after this yields HOLD = 0.
 */
void CREWWATCH_HoldInit(CREWWATCH_HoldState_t *State);

/**
 * \brief Advance by one tick with this tick's latched raw value.
 *
 * Same value as previous tick -> counter + 1 (saturating at
 * CREWWATCH_HOLD_MAX). Any change -> counter = 0. The comparison is on the
 * raw bit pattern, before any scaling, so a change smaller than one
 * feature LSB still resets the counter.
 */
void CREWWATCH_HoldAdvance(CREWWATCH_HoldState_t *State, uint32_t Raw);

/**
 * \brief Scaled HOLD feature value.
 *
 * \param[in]  Def   Feature definition. Its Transform field is ignored;
 *                   Bias/Scale/Shift are applied through the AGE path of
 *                   TLM_WATCH_ApplyTransform().
 * \param[in]  State Channel state (after CREWWATCH_HoldAdvance for this tick)
 * \param[out] Out   int16 feature value
 *
 * \return false if an argument is NULL or the state has never been advanced
 */
bool CREWWATCH_ApplyHold(const TLM_WATCH_FeatureDef_t *Def, const CREWWATCH_HoldState_t *State, int16_t *Out);

#endif /* CREWWATCH_HOLD_H */
