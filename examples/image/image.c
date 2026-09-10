#include <sokol/sokol_gfx.h>
#include <sokol/sokol_app.h>
#include <sokol/sokol_glue.h>
#include <sokol/sokol_log.h>
#include <stb/stb_image.h>
#include <stdio.h>

static const unsigned char kPng[] = {
  0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a,0x00,0x00,0x00,0x0d,0x49,0x48,0x44,0x52,
  0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
  0xde,0x00,0x00,0x00,0x0c,0x49,0x44,0x41,0x54,0x08,0xd7,0x63,0xf8,0xcf,0xc0,0x00,
  0x00,0x03,0x01,0x01,0x00,0x18,0xdd,0x8d,0xb0,0x00,0x00,0x00,0x00,0x49,0x45,0x4e,
  0x44,0xae,0x42,0x60,0x82
};
static sg_image g_img;

static void init(void) {
  sg_setup(&(sg_desc){ .environment = sglue_environment(), .logger.func = slog_func });
  int w = 0, h = 0, comp = 0;
  unsigned char *px = stbi_load_from_memory(kPng, (int)sizeof kPng, &w, &h, &comp, 4);
  if (!px) { fprintf(stderr, "decode failed: %s\n", stbi_failure_reason()); sapp_quit(); return; }
  g_img = sg_make_image(&(sg_image_desc){
      .width = w, .height = h,
      .data.mip_levels[0] = { .ptr = px, .size = (size_t)(w * h * 4) } });
  stbi_image_free(px);
}

static void frame(void) {
  /* The texture exists; drawing it needs a shader, which is the shader
     example's job. Clearing to a colour proves decode + upload succeeded. */
  sg_pass pass = { .action = { .colors[0] = { .load_action = SG_LOADACTION_CLEAR,
                                              .clear_value = { 0.2f, 0.2f, 0.25f, 1.0f } } },
                   .swapchain = sglue_swapchain() };
  sg_begin_pass(&pass);
  sg_end_pass();
  sg_commit();
}

static void cleanup(void) { sg_destroy_image(g_img); sg_shutdown(); }

sapp_desc sokol_main(int argc, char *argv[]) {
  (void)argc; (void)argv;
  return (sapp_desc){ .init_cb = init, .frame_cb = frame, .cleanup_cb = cleanup,
                      .width = 640, .height = 480, .window_title = "gamelib image",
                      .logger.func = slog_func };
}
