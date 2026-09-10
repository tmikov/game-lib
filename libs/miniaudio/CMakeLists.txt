# Pure C. No backend option: miniaudio compiles every backend its platform
# offers (WASAPI, CoreAudio, ALSA, PulseAudio, JACK, sndio, Web Audio) and
# selects at run time.
gamelib_add_library(NAME miniaudio SOURCES src/miniaudio.c)

option(GAMELIB_MINIAUDIO_RUNTIME_LINKING
       "macOS: let miniaudio link CoreAudio frameworks at run time" OFF)

if(APPLE)
  if(GAMELIB_MINIAUDIO_RUNTIME_LINKING)
    # Upstream's default. Nothing to link.
  else()
    # The default here, deliberately: miniaudio warns that runtime framework
    # linking means "your application may not pass Apple's notarization
    # process", and a pack meant for shipping games should default to the
    # notarizable configuration.
    target_compile_definitions(gamelib_miniaudio PRIVATE MA_NO_RUNTIME_LINKING)
    target_link_libraries(gamelib_miniaudio PUBLIC
        "-framework CoreFoundation" "-framework CoreAudio" "-framework AudioToolbox")
  endif()
elseif(EMSCRIPTEN)
  # miniaudio: "You cannot use -std=c* compiler flags, nor -ansi. This only
  # applies to the Emscripten build." Adding no compile features is not enough:
  # C_STANDARD is initialised from CMAKE_C_STANDARD, so a consumer who sets that
  # variable would make CMake emit -std= for our target. Clearing the property
  # touches only our target, so the no-global-state rule still holds.
  #
  # Limitation we cannot fix from here: a -std= the consumer put directly into
  # CMAKE_C_FLAGS. The README says so.
  set_target_properties(gamelib_miniaudio PROPERTIES C_STANDARD "")
elseif(UNIX)
  # miniaudio's own Building section: "The Linux build only requires linking to
  # -ldl, -lpthread and -lm. You do not need any development packages."
  target_link_libraries(gamelib_miniaudio PUBLIC dl m)
  target_compile_options(gamelib_miniaudio PUBLIC -pthread)
  target_link_options(gamelib_miniaudio PUBLIC -pthread)
endif()
# Windows needs nothing.
