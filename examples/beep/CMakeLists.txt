gamelib_add_example(NAME beep SOURCES beep.c LIBS gamelib::sokol_audio gamelib::sokol_log)
target_link_libraries(gamelib_example_beep PRIVATE $<$<NOT:$<PLATFORM_ID:Windows>>:m>)
