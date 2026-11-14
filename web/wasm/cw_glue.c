/************************************************************************
 * CREWWATCH -- WebAssembly glue: the whole on-board chain in the browser
 *
 * Packets -> latch -> tick (AGE, HOLD, RAW via tlm_watch_feature.c)
 *         -> flight window mean (tlm_watch_window.c)
 *         -> score (tinyinfer: MatVec -> MatVec -> SqErr)
 *
 * The arithmetic is the UNMODIFIED flight C code compiled to wasm32. This
 * file holds only static buffers and the latch/tick bookkeeping, mirroring
 * features/bridge.py line by line. tests/test_wasm_bitexact.mjs checks that
 * browser and host produce identical feature vectors and scores.
 *
 * Written during NASA Space Apps 2026 (48 h).
 * Written with AI assistance (Claude Code), see AI_USE.md.
 * Licensed under the Apache License, Version 2.0
 ************************************************************************/

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "tinyinfer.h"
#include "tlm_watch_feature.h"
#include "tlm_watch_window.h"
#include "crewwatch_hold.h"
#include "crewwatch_checkin.h"

#define CW_MAX_F    32
#define CW_MAX_SRC  8
#define CW_PKT_MAX  64
#define CW_XFORM_HOLD 4   /* CrewWatch-local; routed through the AGE scaling */

static TLM_WATCH_FeatureDef_t Defs[CW_MAX_F];
static uint8_t                Xform[CW_MAX_F];       /* as given by the caller (HOLD = 4) */
static TLM_WATCH_FeatState_t  DState[CW_MAX_F];
static CREWWATCH_HoldState_t  HState[CW_MAX_F];
static uint32_t               Raw[CW_MAX_F];
static bool                   RawValid[CW_MAX_F];
static uint16_t               Age[CW_MAX_SRC];
static bool                   Updated[CW_MAX_SRC];
static uint16_t               NFeat, NSrc;
static int16_t                Vec[CW_MAX_F];
static int16_t                WMean[CW_MAX_F];
static bool                   WMeanValid;
static TLM_WATCH_Window_t     Win;
static uint8_t                Pkt[CW_PKT_MAX];

/* two models (0 = fast, 1 = slow), F x F each, ACT_NONE (Mahalanobis chain) */
static int8_t  WEnc[2][CW_MAX_F * CW_MAX_F];
static int8_t  WDec[2][CW_MAX_F * CW_MAX_F];
static int32_t MultEnc[2], ShiftEnc[2], MultDec[2], ShiftDec[2];
static int16_t Hidden[CW_MAX_F], Recon[CW_MAX_F];
static int32_t Contrib[CW_MAX_F];

/* ---- buffers the JS side fills ---- */
TLM_WATCH_FeatureDef_t *CW_Defs(void) { return Defs; }
uint8_t *CW_Xforms(void) { return Xform; }
uint8_t *CW_PktBuf(void) { return Pkt; }
int8_t *CW_WEnc(int32_t M) { return WEnc[M & 1]; }
int8_t *CW_WDec(int32_t M) { return WDec[M & 1]; }
int16_t *CW_Vec(void) { return Vec; }
int16_t *CW_WMean(void) { return WMean; }
int32_t *CW_Contrib(void) { return Contrib; }
uint16_t *CW_Ages(void) { return Age; }
int32_t CW_DefSize(void) { return (int32_t)sizeof(TLM_WATCH_FeatureDef_t); }

/** Call after filling CW_Defs()/CW_Xforms(). Mirrors bridge.Engine.reset(). */
int32_t CW_Init(uint16_t NumFeatures, uint16_t NumSources)
{
    uint16_t i;
    if (NumFeatures == 0u || NumFeatures > CW_MAX_F || NumSources == 0u || NumSources > CW_MAX_SRC)
    {
        return 0;
    }
    NFeat = NumFeatures;
    NSrc  = NumSources;
    for (i = 0; i < NFeat; ++i)
    {
        if (Xform[i] == CW_XFORM_HOLD)
        {
            Defs[i].Transform = TLM_WATCH_XFORM_AGE; /* never read by ApplyHold */
        }
        else
        {
            Defs[i].Transform = Xform[i];
        }
        DState[i].PrevRaw = 0u;
        DState[i].HasPrev = false;
        CREWWATCH_HoldInit(&HState[i]);
        Raw[i]      = 0u;
        RawValid[i] = false;
    }
    for (i = 0; i < NSrc; ++i)
    {
        Age[i]     = 0xFFFFu; /* flight latch starts at max, not 0 */
        Updated[i] = false;
    }
    WMeanValid = false;
    return TLM_WATCH_WindowInit(&Win, NFeat) ? 1 : 0;
}

/** Packet of Len bytes already copied to CW_PktBuf(). Mirrors Engine.latch(). */
void CW_Latch(uint16_t Src, uint32_t Len)
{
    uint16_t i;
    uint32_t V;
    if (Len > CW_PKT_MAX || Src >= NSrc)
    {
        return;
    }
    for (i = 0; i < NFeat; ++i)
    {
        if (Defs[i].SourceIdx != Src || Xform[i] == TLM_WATCH_XFORM_AGE)
        {
            continue;
        }
        if (TLM_WATCH_ExtractRaw(Pkt, Len, Defs[i].Offset, Defs[i].Type, &V))
        {
            Raw[i]      = V;
            RawValid[i] = true;
        }
    }
    Updated[Src] = true;
}

/** One sampling tick. Returns 1 if Vec is valid. Mirrors Engine.tick() + window. */
int32_t CW_Tick(void)
{
    uint16_t s, i;
    bool     AllOk = true;
    bool     Ok;
    int16_t  Out;

    for (s = 0; s < NSrc; ++s)
    {
        if (Updated[s])
        {
            Age[s]     = 0u;
            Updated[s] = false;
        }
        else if (Age[s] < 0xFFFFu)
        {
            Age[s]++;
        }
    }

    for (i = 0; i < NFeat; ++i)
    {
        Out = 0;
        if (Xform[i] == TLM_WATCH_XFORM_AGE)
        {
            Ok = TLM_WATCH_ApplyTransform(&Defs[i], 0u, Age[Defs[i].SourceIdx], &DState[i], &Out);
        }
        else if (!RawValid[i])
        {
            AllOk = false;
            Vec[i] = 0;
            continue;
        }
        else if (Xform[i] == CW_XFORM_HOLD)
        {
            CREWWATCH_HoldAdvance(&HState[i], Raw[i]);
            Ok = CREWWATCH_ApplyHold(&Defs[i], &HState[i], &Out);
        }
        else
        {
            Ok = TLM_WATCH_ApplyTransform(&Defs[i], Raw[i], Age[Defs[i].SourceIdx], &DState[i], &Out);
            if (Xform[i] == TLM_WATCH_XFORM_DIFF)
            {
                TLM_WATCH_AdvanceState(&DState[i], Raw[i]);
            }
        }
        Vec[i] = Ok ? Out : 0;
        if (!Ok)
        {
            AllOk = false;
        }
    }

    WMeanValid = false;
    if (AllOk)
    {
        TLM_WATCH_WindowPush(&Win, Vec);
        if (TLM_WATCH_WindowIsFull(&Win))
        {
            WMeanValid = TLM_WATCH_WindowMean(&Win, WMean);
        }
    }
    return AllOk ? 1 : 0;
}

int32_t CW_WMeanValid(void) { return WMeanValid ? 1 : 0; }

uint16_t CW_HoldTicks(uint16_t Idx) { return (Idx < NFeat) ? HState[Idx].HoldTicks : 0u; }

void CW_SetModel(int32_t M, int32_t MultE, int32_t ShiftE, int32_t MultD, int32_t ShiftD)
{
    M &= 1;
    MultEnc[M]  = MultE;
    ShiftEnc[M] = ShiftE;
    MultDec[M]  = MultD;
    ShiftDec[M] = ShiftD;
}

/** Same order as tinyinfer_ctypes.Model.score / tlm_watch_score.c (ACT_NONE). */
int32_t CW_Score(int32_t M, const int16_t *X)
{
    M &= 1;
    TINYINFER_MatVec_s8s16(WEnc[M], X, Hidden, NFeat, NFeat, MultEnc[M], (int8_t)ShiftEnc[M]);
    TINYINFER_MatVec_s8s16(WDec[M], Hidden, Recon, NFeat, NFeat, MultDec[M], (int8_t)ShiftDec[M]);
    return TINYINFER_SqErr_s16(X, Recon, Contrib, NFeat);
}

/* ---- astronaut self check-in (crewwatch_checkin.c) ---- */
static CREWWATCH_CheckIn_t       CheckIn;
static CREWWATCH_CheckInResult_t CheckInRes;
static uint8_t                   Moods[64];

CREWWATCH_CheckIn_t *CW_CheckInBuf(void) { return &CheckIn; }
CREWWATCH_CheckInResult_t *CW_CheckInResult(void) { return &CheckInRes; }
uint8_t *CW_MoodBuf(void) { return Moods; }

/** Evaluate CW_CheckInBuf() against an explicit wearable reading. 1 = ok, 0 = rejected input. */
int32_t CW_EvalCheckIn(uint16_t WearableHrX10, uint16_t WearableAge)
{
    return CREWWATCH_EvaluateCheckIn(&CheckIn, WearableHrX10, WearableAge, &CheckInRes) ? 1 : 0;
}

uint16_t CW_LowMoodStreak(uint16_t N) { return CREWWATCH_LowMoodStreak(Moods, (N > 64u) ? 64u : N); }
