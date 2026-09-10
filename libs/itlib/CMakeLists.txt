# Header-only. All 36 upstream headers are vendored: an unused header costs a
# consumer nothing, and choosing a subset would mean revisiting the choice every
# time someone wants one more.
gamelib_add_interface_library(NAME itlib FEATURES cxx_std_11)
# cxx_std_11 is the FLOOR, not the range. Upstream documents a per-header
# standard: most are C++11; pmr_allocator.hpp, rand_dist.hpp and strutil.hpp
# require C++17; generator.hpp and opt_ref_buffer.hpp require C++20. Declaring
# the maximum here would impose C++20 on every user of the cheapest header, so
# the consumer opts in themselves for the headers that need it. The README
# reproduces the table.
