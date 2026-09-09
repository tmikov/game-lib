add_executable(clear clear.c)
target_link_libraries(clear PRIVATE
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::sokol_time)
