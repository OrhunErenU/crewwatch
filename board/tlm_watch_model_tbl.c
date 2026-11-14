/************************************************************************
 * TLM_WATCH -- model tablosu
 *
 * !!! BU DOSYA URETILDI -- ELLE DUZENLEMEYIN !!!
 * Ureten: ground/quantize.py
 * CrewWatch FAST Mahalanobis F=9, threshold from INTEGER model on validation
 ************************************************************************/

#include "cfe_tbl_filedef.h"
#include "tlm_watch_tbl.h"

#define F 9
#define H 9

#define ENC_OFFSET 0
#define DEC_OFFSET 81

/*
 * Kuantalama olcekleri (bilgi amacli; ucus kodu kullanmiyor):
 *   scale_enc    = 0.00719340828
 *   scale_dec    = 0.00787401575
 *   scale_hidden = 1
 *
 * Gercel carpanlar ve Q31 karsiliklari:
 *   enc: M = 0.00719340828  ->  mult=1977309011, shift=-7
 *        geri cevrim = 0.00719340828  (bagil hata 6.227e-11)
 *   dec: M = 0.00787401575  ->  mult=1082196484, shift=-6
 *        geri cevrim = 0.00787401575  (bagil hata 2.910e-11)
 */

TLM_WATCH_ModelTbl_t TLM_WATCH_ModelTbl = {

    .Enc = {.Rows = H, .Cols = F,
            .Multiplier = 1977309011, .Shift = -7,
            .ActType = TINYINFER_ACT_NONE, .Pad = {0, 0}},

    .Dec = {.Rows = F, .Cols = H,
            .Multiplier = 1082196484, .Shift = -6,
            .ActType = TINYINFER_ACT_NONE, .Pad = {0, 0}},

    .EncOffset = ENC_OFFSET,
    .DecOffset = DEC_OFFSET,

    /*
     * Esik ground/calibrate.py tarafindan, TAMSAYI modelin urettigi
     * skor dagilimindan secildi (plan Sec. 6). Float dagilimdan
     * secilseydi ucustaki yanlis pozitif orani sessizce kayardi.
     */
    .Threshold = 688768,

    .NumFeatures = F,

    .Weights = {
        /* --- kodlayici: H x F --- */
         112,  -11,   19,    0,    4,    1,    5,    0,    0,    0,  119,  -19,   -1,    2,    0,    1,
           0,    0,    0,    0,  104,   -2,    2,    1,    3,    0,    0,    0,    0,    0,  127,    1,
          -1,   -2,    0,    0,    0,    0,    0,    0,  116,   -1,    0,    0,    0,    0,    0,    0,
           0,    0,    1,    0,    1,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
           0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,    0,
           0,

        /* --- cozucu: F x H --- */
         127,    0,    0,    0,    0,    0,    0,    0,    0,    0,  127,    0,    0,    0,    0,    0,
           0,    0,    0,    0,  127,    0,    0,    0,    0,    0,    0,    0,    0,    0,  127,    0,
           0,    0,    0,    0,    0,    0,    0,    0,  127,    0,    0,    0,    0,    0,    0,    0,
           0,    0,  127,    0,    0,    0,    0,    0,    0,    0,    0,    0,  127,    0,    0,    0,
           0,    0,    0,    0,    0,    0,  127,    0,    0,    0,    0,    0,    0,    0,    0,    0,
         127,
    }
};

CFE_TBL_FILEDEF(TLM_WATCH_ModelTbl, TLM_WATCH.ModelTbl, TLM_WATCH model, tlm_watch_model.tbl)
