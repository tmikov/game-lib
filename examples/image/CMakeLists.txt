add_executable(image image.c)
target_link_libraries(image PRIVATE
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::stb_image)
