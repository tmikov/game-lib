# WIN32 is required on Windows and ignored everywhere else: sokol_app
# supplies WinMain rather than main there, so the executable has to go in
# the GUI subsystem or the linker reports an unresolved `main`.
add_executable(image WIN32 image.c)
target_link_libraries(image PRIVATE
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::stb_image)
