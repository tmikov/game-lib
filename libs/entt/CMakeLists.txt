# Header-only: only upstream's amalgamated header is vendored, which is what
# upstream ships for exactly this use.
gamelib_add_interface_library(NAME entt FEATURES cxx_std_20)
# cxx_std_20 is upstream's own requirement (target_compile_features(EnTT
# INTERFACE cxx_std_20)) and the highest language bar in the pack. A consumer
# linking gamelib::entt opts their whole target into C++20.
