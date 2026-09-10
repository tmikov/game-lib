gamelib_add_example(NAME audio SOURCES audio.c LIBS gamelib::miniaudio)
target_link_libraries(gamelib_example_audio PRIVATE $<$<NOT:$<PLATFORM_ID:Windows>>:m>)
