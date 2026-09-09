add_executable(beep beep.c)
target_link_libraries(beep PRIVATE
    gamelib::sokol_audio
    gamelib::sokol_log
    # beep.c calls sinf() itself; gamelib::sokol_audio does not need libm.
    $<$<NOT:$<PLATFORM_ID:Windows>>:m>)
