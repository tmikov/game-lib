add_executable(physics physics.c)
target_link_libraries(physics PRIVATE gamelib::box2d)
