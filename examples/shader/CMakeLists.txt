# WIN32 is required on Windows and ignored everywhere else: sokol_app
# supplies WinMain rather than main there, so the executable has to go in
# the GUI subsystem or the linker reports an unresolved `main`.
add_executable(shader WIN32 shader.c)
target_link_libraries(shader PRIVATE
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log)

# Compiles triangle.glsl to triangle.h at build time and attaches it to the
# target. Regenerates when the shader, anything it @includes, or the vendored
# sokol-shdc binary changes.
gamelib_add_shader(TARGET shader INPUT triangle.glsl OUTPUT triangle.h)
