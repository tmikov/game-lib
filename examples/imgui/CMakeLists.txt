# WIN32 is required on Windows and ignored everywhere else: sokol_app
# supplies WinMain rather than main there, so the executable has to go in
# the GUI subsystem or the linker reports an unresolved `main`.
add_executable(imgui-demo WIN32 imgui.cc)
target_link_libraries(imgui-demo PRIVATE
    gamelib::sokol_imgui
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::imgui)
