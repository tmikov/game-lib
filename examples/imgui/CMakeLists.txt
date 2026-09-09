add_executable(imgui-demo imgui.cc)
target_link_libraries(imgui-demo PRIVATE
    gamelib::sokol_imgui
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::imgui)
