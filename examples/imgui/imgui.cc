/* The brief's snippet used C99 compound literals with nested/array designators
   (e.g. "&(sg_desc){ .environment = ..., .logger.func = ... }" and
   ".action.colors[0] = {...}"). Neither compiles as C++: compound literals are
   not part of the C++ grammar at all, and C++20 designated initializers only
   name one non-static data member per level -- no dotted paths, no array
   subscripts. This file is compiled as C++ (see libs/sokol/src/sokol_imgui.cc),
   so every sokol/imgui call below builds its descriptor as a named,
   zero-initialized local and assigns fields instead. */
#include <sokol/sokol_gfx.h>
#include <sokol/sokol_app.h>
#include <sokol/sokol_glue.h>
#include <sokol/sokol_log.h>
#include <imgui/imgui.h>
#include <sokol/sokol_imgui.h>

static void init(void) {
  sg_desc desc = {};
  desc.environment = sglue_environment();
  desc.logger.func = slog_func;
  sg_setup(&desc);

  simgui_desc_t simgui_desc = {};
  simgui_desc.logger.func = slog_func;
  simgui_setup(&simgui_desc);
}

static void frame(void) {
  simgui_frame_desc_t frame_desc = {};
  frame_desc.width = sapp_width();
  frame_desc.height = sapp_height();
  frame_desc.delta_time = sapp_frame_duration();
  frame_desc.dpi_scale = sapp_dpi_scale();
  simgui_new_frame(&frame_desc);

  ImGui::ShowDemoWindow();

  sg_pass pass = {};
  pass.action.colors[0].load_action = SG_LOADACTION_CLEAR;
  pass.action.colors[0].clear_value = { 0.1f, 0.1f, 0.12f, 1.0f };
  pass.swapchain = sglue_swapchain();
  sg_begin_pass(&pass);
  simgui_render();
  sg_end_pass();
  sg_commit();
}

static void event(const sapp_event *ev) { simgui_handle_event(ev); }
static void cleanup(void) { simgui_shutdown(); sg_shutdown(); }

sapp_desc sokol_main(int argc, char *argv[]) {
  (void)argc; (void)argv;
  sapp_desc desc = {};
  desc.init_cb = init;
  desc.frame_cb = frame;
  desc.event_cb = event;
  desc.cleanup_cb = cleanup;
  desc.width = 1024;
  desc.height = 768;
  desc.window_title = "gamelib imgui";
  desc.logger.func = slog_func;
  return desc;
}
