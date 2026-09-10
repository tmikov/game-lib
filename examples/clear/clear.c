#include <sokol/sokol_gfx.h>
#include <sokol/sokol_app.h>
#include <sokol/sokol_glue.h>
#include <sokol/sokol_log.h>
#include <sokol/sokol_time.h>

static uint64_t g_start;

static void init(void) {
  sg_setup(&(sg_desc){ .environment = sglue_environment(), .logger.func = slog_func });
  stm_setup();
  g_start = stm_now();
}

static void frame(void) {
  /* Pulse the clear colour so the window is visibly alive. */
  const float t = (float)stm_sec(stm_since(g_start));
  const float r = 0.5f + 0.5f * (float)((int)(t * 2.0f) % 2);
  sg_pass pass = { .action = { .colors[0] = { .load_action = SG_LOADACTION_CLEAR,
                                              .clear_value = { r, 0.2f, 0.3f, 1.0f } } },
                   .swapchain = sglue_swapchain() };
  sg_begin_pass(&pass);
  sg_end_pass();
  sg_commit();
}

static void cleanup(void) { sg_shutdown(); }

sapp_desc sokol_main(int argc, char *argv[]) {
  (void)argc; (void)argv;
  return (sapp_desc){ .init_cb = init, .frame_cb = frame, .cleanup_cb = cleanup,
                      .width = 640, .height = 480, .window_title = "gamelib clear",
                      .logger.func = slog_func };
}
