// Preserve star detail while containing the additive silver-core highlights.
layout(location=0) out vec4 fragColor;
void main(){
    vec3 stars=texture(sTD2DInputs[0],vUV.st).rgb;
    vec3 nebula=texture(sTD2DInputs[1],vUV.st).rgb;
    vec3 light=max(stars+nebula,vec3(0.));
    // Luminance tone mapping preserves the warm core instead of clipping each
    // color channel independently as star density grows.
    float luminance=dot(light,vec3(.2126,.7152,.0722));
    float x=luminance*.85;
    float mapped=(x*(2.51*x+.03))/(x*(2.43*x+.59)+.14);
    vec3 color=light*(mapped/max(luminance,1.e-6));
    color=pow(clamp(color,0.,1.),vec3(1./2.2));
    fragColor=TDOutputSwizzle(vec4(color,1.));
}
