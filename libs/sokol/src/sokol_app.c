/* Include order is required by sokol_glue.h and must not be sorted:
   sokol_gfx.h before the glue declaration, sokol_app.h before the glue
   implementation. sokol_glue.h #errors otherwise. */
#define SOKOL_APP_IMPL
#include <sokol/sokol_app.h>

#include <sokol/sokol_gfx.h>

#define SOKOL_GLUE_IMPL
#include <sokol/sokol_glue.h>
