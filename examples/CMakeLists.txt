# Examples are added here as later tasks vendor the libraries they demonstrate.

# Each example is declared only when every target it needs exists, so a disabled
# library or a headless backend removes its example instead of erroring.
gamelib_have_targets(_ok sokol_app sokol_gfx sokol_log sokol_time)
if(_ok)
  add_subdirectory(clear)
else()
  message(STATUS "game-lib: example 'clear' skipped (needs sokol_app)")
endif()

gamelib_have_targets(_ok sokol_app sokol_gfx sokol_log stb_image)
if(_ok)
  add_subdirectory(image)
else()
  message(STATUS "game-lib: example 'image' skipped (needs sokol_app and stb_image)")
endif()

gamelib_have_targets(_ok sokol_audio sokol_log)
if(_ok)
  add_subdirectory(beep)
else()
  message(STATUS "game-lib: example 'beep' skipped (needs sokol_audio)")
endif()

gamelib_have_targets(_ok miniaudio)
if(_ok)
  add_subdirectory(audio)
else()
  message(STATUS "game-lib: example 'audio' skipped (needs miniaudio)")
endif()

gamelib_have_targets(_ok sokol_imgui sokol_app sokol_gfx sokol_log imgui)
if(_ok)
  add_subdirectory(imgui)
else()
  message(STATUS "game-lib: example 'imgui' skipped (needs sokol_imgui)")
endif()

gamelib_have_targets(_ok box2d)
if(_ok)
  add_subdirectory(physics)
else()
  message(STATUS "game-lib: example 'physics' skipped (needs box2d)")
endif()

gamelib_have_targets(_ok sokol_app sokol_gfx sokol_log)
if(_ok AND NOT GAMELIB_SHDC_SLANG STREQUAL "")
  add_subdirectory(shader)
else()
  message(STATUS "game-lib: example 'shader' skipped (needs sokol_app and a real backend)")
endif()
