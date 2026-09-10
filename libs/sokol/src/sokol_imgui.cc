/* Compiled as C++ so sokol_imgui calls the Dear ImGui C++ API directly. That is
   what removes any need for cimgui.

   The include order below is required by sokol_imgui.h and must not be sorted:
   sokol_gfx.h and sokol_app.h before the declaration, imgui.h before the
   implementation. */
#include <sokol/sokol_gfx.h>
#include <sokol/sokol_app.h>

#include <imgui/imgui.h>

#define SOKOL_IMGUI_IMPL
#include <sokol/sokol_imgui.h>
