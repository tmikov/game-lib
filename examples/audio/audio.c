/* Synthesises a WAV in memory and plays it through ma_engine, which is the
   high-level path: ma_engine + ma_sound, not the raw device API. */
#include <miniaudio/miniaudio.h>
#include <math.h>
#include <stdio.h>

#define FRAMES 44100

int main(void) {
  static float samples[FRAMES];
  for (int i = 0; i < FRAMES; ++i)
    samples[i] = 0.2f * sinf(2.0f * 3.14159265f * 440.0f * (float)i / 44100.0f);

  ma_audio_buffer_config cfg =
      ma_audio_buffer_config_init(ma_format_f32, 1, FRAMES, samples, NULL);
  ma_audio_buffer buffer;
  if (ma_audio_buffer_init(&cfg, &buffer) != MA_SUCCESS) {
    fprintf(stderr, "buffer init failed\n"); return 1;
  }

  ma_engine engine;
  if (ma_engine_init(NULL, &engine) != MA_SUCCESS) {
    fprintf(stderr, "no audio device\n"); ma_audio_buffer_uninit(&buffer); return 1;
  }

  ma_sound sound;
  if (ma_sound_init_from_data_source(&engine, &buffer, 0, NULL, &sound) != MA_SUCCESS) {
    fprintf(stderr, "sound init failed\n");
    ma_engine_uninit(&engine); ma_audio_buffer_uninit(&buffer); return 1;
  }
  ma_sound_start(&sound);
  while (ma_sound_is_playing(&sound)) { /* spin until the second is up */ }

  ma_sound_uninit(&sound);
  ma_engine_uninit(&engine);
  ma_audio_buffer_uninit(&buffer);
  return 0;
}
