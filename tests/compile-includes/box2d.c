#include <box2d/box2d.h>
int gamelib_probe_box2d(void) { b2WorldDef d = b2DefaultWorldDef(); return d.enableSleep; }
