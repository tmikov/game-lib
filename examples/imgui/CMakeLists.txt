gamelib_add_example(NAME imgui SOURCES imgui.cc
    LIBS gamelib::sokol_imgui gamelib::sokol_app gamelib::sokol_gfx
         gamelib::sokol_log gamelib::imgui)
