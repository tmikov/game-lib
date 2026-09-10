#include <itlib/span.hpp>
#include <itlib/small_vector.hpp>
int gamelib_probe_itlib() {
  itlib::small_vector<int, 4> v{1, 2, 3};
  itlib::span<int> s(v.data(), v.size());
  return (int)s.size();
}
