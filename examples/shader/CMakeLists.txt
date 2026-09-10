gamelib_add_example(NAME shader SOURCES shader.c
    LIBS gamelib::sokol_app gamelib::sokol_gfx gamelib::sokol_log)
gamelib_add_shader(TARGET gamelib_example_shader INPUT triangle.glsl OUTPUT triangle.h)
