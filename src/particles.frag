in vec4 vParticle;
layout(location = 0) out vec4 fragColor;
void main() {
    vec2 p = TDPointCoord() * 2.0 - 1.0;
    float d = dot(p,p);
    if (d > 1.0) discard;
    float light = exp(-d*5.5) + 0.35*exp(-d*32.0);
    fragColor = TDOutputSwizzle(vec4(vParticle.rgb * light, light));
}
