#include <sokol/sokol_audio.h>
#include <sokol/sokol_log.h>
#include <math.h>
#include <stdio.h>

int main(void) {
  saudio_setup(&(saudio_desc){ .logger.func = slog_func });
  if (!saudio_isvalid()) { fprintf(stderr, "no audio device\n"); return 1; }

  const int rate = saudio_sample_rate();
  float phase = 0.0f;
  const float step = 2.0f * 3.14159265f * 440.0f / (float)rate;

  /* Push about a second of a 440 Hz sine, then stop. */
  for (int pushed = 0; pushed < rate; ) {
    int want = saudio_expect();
    if (want <= 0) continue;
    static float buf[1024];
    if (want > 1024) want = 1024;
    for (int i = 0; i < want; ++i) { buf[i] = 0.2f * sinf(phase); phase += step; }
    pushed += saudio_push(buf, want);
  }
  saudio_shutdown();
  return 0;
}
