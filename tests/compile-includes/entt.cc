#include <entt/entt.hpp>
/* Instantiating a registry is what actually exercises C++20 in EnTT v4. */
void gamelib_probe_entt() { entt::registry r; (void)r.create(); }
