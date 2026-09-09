add_executable(audio audio.c)
target_link_libraries(audio PRIVATE
    gamelib::miniaudio
    # audio.c calls sinf() itself to synthesise the tone.
    $<$<NOT:$<PLATFORM_ID:Windows>>:m>)
