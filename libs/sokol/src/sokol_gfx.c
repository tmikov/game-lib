/* Per-header impl macro, not the blanket SOKOL_IMPL: the TUs are split so that
   a consumer linking sokol_gfx pulls in no windowing code. */
#define SOKOL_GFX_IMPL
#include <sokol/sokol_gfx.h>
