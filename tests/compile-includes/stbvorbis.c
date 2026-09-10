#define STB_VORBIS_HEADER_ONLY
#include <stb/stb_vorbis.c>
int gamelib_probe_vorbis(void) { return (int)sizeof(stb_vorbis_info); }
