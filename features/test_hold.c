/************************************************************************
 * Host test for crewwatch_hold.c -- build: features/build_host.sh
 * Written with AI assistance (Claude Code), see AI_USE.md.
 ************************************************************************/

#include <stdio.h>
#include <string.h>

#include "crewwatch_hold.h"

static int Fails = 0;
static int Checks = 0;

#define CHECK(cond, msg)                                      \
    do                                                        \
    {                                                         \
        Checks++;                                             \
        if (!(cond))                                          \
        {                                                     \
            Fails++;                                          \
            printf("  FAIL  %s (line %d)\n", msg, __LINE__); \
        }                                                     \
    } while (0)

static TLM_WATCH_FeatureDef_t MkDef(int32_t Bias, int32_t Scale, int8_t Shift)
{
    TLM_WATCH_FeatureDef_t D;
    memset(&D, 0, sizeof(D));
    D.Transform = TLM_WATCH_XFORM_RAW; /* deliberately not AGE: must be ignored */
    D.Bias      = Bias;
    D.Scale     = Scale;
    D.Shift     = Shift;
    return D;
}

int main(void)
{
    CREWWATCH_HoldState_t  S;
    TLM_WATCH_FeatureDef_t D = MkDef(0, 1, 0);
    int16_t                Out = 0;
    uint32_t               i;

    /* 1. never advanced -> no value (warm-up, like DIFF) */
    CREWWATCH_HoldInit(&S);
    CHECK(!CREWWATCH_ApplyHold(&D, &S, &Out), "uninitialised state yields no value");

    /* 2. first sample -> 0 */
    CREWWATCH_HoldAdvance(&S, 700u);
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == 0, "first tick HOLD = 0");

    /* 3. same value 5 more ticks -> 5 */
    for (i = 0; i < 5u; ++i)
    {
        CREWWATCH_HoldAdvance(&S, 700u);
    }
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == 5, "five repeats HOLD = 5");

    /* 4. one LSB change resets */
    CREWWATCH_HoldAdvance(&S, 701u);
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == 0, "1-LSB change resets HOLD");

    /* 5. going back to an older value is still a change */
    CREWWATCH_HoldAdvance(&S, 700u);
    CHECK(S.HoldTicks == 0u, "A->B->A counts as change");

    /* 6. saturates at 0xFFFF, does not wrap */
    S.HoldTicks = (uint16_t)(CREWWATCH_HOLD_MAX - 1u);
    CREWWATCH_HoldAdvance(&S, 700u);
    CHECK(S.HoldTicks == CREWWATCH_HOLD_MAX, "reaches ceiling");
    CREWWATCH_HoldAdvance(&S, 700u);
    CHECK(S.HoldTicks == CREWWATCH_HOLD_MAX, "stays at ceiling (no wrap)");

    /* 7. scaling goes through the AGE path: ((65535 - 0) * 1) >> 0 saturates int16 */
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == 32767, "int16 saturation via AGE path");

    /* 8. Bias/Scale/Shift applied: ((10 - 2) * 3) >> 1 = 12 */
    CREWWATCH_HoldInit(&S);
    for (i = 0; i < 11u; ++i)
    {
        CREWWATCH_HoldAdvance(&S, 0xDEADBEEFu);
    }
    D = MkDef(2, 3, 1);
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == 12, "((10-2)*3)>>1 = 12");

    /* 9. negative result: ((0 - 4) * 8) >> 2 = -8 (arithmetic shift, as in tlm_watch) */
    CREWWATCH_HoldInit(&S);
    CREWWATCH_HoldAdvance(&S, 5u);
    D = MkDef(4, 8, 2);
    CHECK(CREWWATCH_ApplyHold(&D, &S, &Out) && Out == -8, "((0-4)*8)>>2 = -8");

    /* 10. caller's definition is not modified */
    CHECK(D.Transform == TLM_WATCH_XFORM_RAW, "Def->Transform untouched");

    /* 11. NULL safety */
    CHECK(!CREWWATCH_ApplyHold(NULL, &S, &Out), "NULL def");
    CHECK(!CREWWATCH_ApplyHold(&D, NULL, &Out), "NULL state");
    CHECK(!CREWWATCH_ApplyHold(&D, &S, NULL), "NULL out");
    CREWWATCH_HoldAdvance(NULL, 1u); /* must not crash */
    CREWWATCH_HoldInit(NULL);

    /* 12. full 32-bit pattern compared, not just low bits */
    CREWWATCH_HoldInit(&S);
    CREWWATCH_HoldAdvance(&S, 0x00010000u);
    CREWWATCH_HoldAdvance(&S, 0x00020000u);
    CHECK(S.HoldTicks == 0u, "high-bit change detected");

    printf("crewwatch_hold: %d/%d checks passed\n", Checks - Fails, Checks);
    return Fails == 0 ? 0 : 1;
}
