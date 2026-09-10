/* A box falling onto static ground, stepped headlessly and reported on stdout.
   No renderer: this example exists to prove the target links and steps, and it
   is the one example CI can actually run. */
#include <box2d/box2d.h>
#include <stdio.h>

int main(void) {
  b2WorldDef wd = b2DefaultWorldDef();
  wd.gravity = (b2Vec2){ 0.0f, -10.0f };
  b2WorldId world = b2CreateWorld(&wd);

  b2BodyDef gd = b2DefaultBodyDef();
  gd.position = (b2Vec2){ 0.0f, -1.0f };
  b2BodyId ground = b2CreateBody(world, &gd);
  b2Polygon groundBox = b2MakeBox(50.0f, 1.0f);
  b2ShapeDef groundSd = b2DefaultShapeDef();
  b2CreatePolygonShape(ground, &groundSd, &groundBox);

  b2BodyDef bd = b2DefaultBodyDef();
  bd.type = b2_dynamicBody;
  bd.position = (b2Vec2){ 0.0f, 10.0f };
  b2BodyId box = b2CreateBody(world, &bd);
  b2Polygon dynBox = b2MakeBox(0.5f, 0.5f);
  b2ShapeDef sd = b2DefaultShapeDef();
  sd.density = 1.0f;
  b2CreatePolygonShape(box, &sd, &dynBox);

  for (int i = 0; i < 180; ++i) b2World_Step(world, 1.0f / 60.0f, 4);

  b2Vec2 p = b2Body_GetPosition(box);
  printf("box came to rest at y=%.3f\n", p.y);
  b2DestroyWorld(world);

  /* It started at y=10 and must have fallen onto the ground near y=0.5. */
  return (p.y > 0.0f && p.y < 1.5f) ? 0 : 1;
}
