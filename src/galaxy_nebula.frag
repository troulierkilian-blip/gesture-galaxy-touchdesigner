// @include galaxy_common.glsl
// Main emission/absorption volume; outer clusters use analytic ray integrals.
layout(location=0) out vec4 fragColor;
const int VOLUME_STEPS=16;
vec4 medium(vec3 p){
    p.xy/=DISK_RADIUS_GAIN;
    p.z-=diskWarp(p.xy);
    float r=length(p.xy),phase=atan(p.y,p.x)-spiralAngle(r);
    float arm=pow(.5+.5*cos(4.*phase),12.);
    float branch=pow(.5+.5*cos(4.*(phase-branchWindow(r)*branchAngle(r))),24.)*branchWindow(r)*.38;
    float envelope=exp(-r*.66)*(1.-smoothstep(2.05,2.65,r))*smoothstep(.07,.48,r);
    float clouds=cloudNoise(p*vec3(4.,4.,8.));
    float filaments=noise3(p*vec3(17.,17.,24.));
    float height=.056+.064*r;
    float slab=exp(-.5*p.z*p.z/(height*height))/(2.5066*height);
    float density=(arm+branch)*envelope*slab;
    float dust=dustField(p);
    float textureWeight=.24+.90*smoothstep(.24,.77,clouds)*(.65+.35*filaments);
    vec3 arms=mix(coolColor(),accentColor(),clouds)*density*textureWeight*.25*(1.+uMotion.w*.4);
    float core=exp(-sqrt(r*r+p.z*p.z*1.8)*7.5)*.88;
    core+=exp(-r*r*5.-p.z*p.z*22.)*.12;
    vec3 center=vec3(1.,.83,.62)*core*(1.+uMotion.w*.65);
    vec3 halo=mix(coolColor(),vec3(.44,.38,.36),.5)*exp(-r*2.-p.z*p.z*7.)*.035;
    float extinction=density*dust*.60;
    return vec4(arms+center+halo,extinction);
}
// A Gaussian ellipsoid integrated along the forward camera ray. The cluster
// volume does not increase the main disk's integration interval.
float erfApprox(float x){
    float s=sign(x);x=abs(x);
    float t=1./(1.+.3275911*x);
    float polynomial=(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t;
    return s*(1.-polynomial*exp(-x*x));
}
float gaussianRay(vec3 ro,vec3 rd,vec3 center,vec3 sigma,float angle){
    vec3 q=ro-center,d=rd;
    q.xy=turn(-angle)*q.xy;d.xy=turn(-angle)*d.xy;
    q/=sigma;d/=sigma;
    float A=dot(d,d),B=dot(q,d);
    float distance2=max(0.,dot(q,q)-B*B/A);
    // Integrate only t>=0, continuously even when a cluster crosses the camera.
    float forward=.5*(1.-erfApprox(B/sqrt(2.*A)));
    return forward*exp(-.5*distance2)/(sqrt(A)*pow(sigma.x*sigma.y*sigma.z,1./3.));
}
vec3 surroundingClouds(vec3 ro,vec3 rd){
    vec3 light=vec3(0.);
    for(int i=0;i<8;i++){
        vec3 center=clusterCenter(i);
        float radius=clusterRadius(i),angle=float(i)*.7;
        float core=gaussianRay(ro,rd,center,radius*vec3(1.,.75,.85),angle);
        float halo=gaussianRay(ro,rd,center,radius*vec3(2.6,2.,2.3),angle);
        float tangent=atan(center.y,center.x);
        vec3 cloudCenter=center*1.03+vec3(0.,0.,.12*sin(float(i)*2.3));
        float wisp=gaussianRay(ro,rd,cloudCenter,vec3(radius*1.6,.55,radius*1.8),tangent);
        light+=clusterColor(i)*(core*.032+halo*.009+wisp*.008)*(1.+uMotion.w*.13);
    }
    return light;
}
void main(){
    vec3 ray=normalize(vec3((vUV.st-.5)*uProjection.yz,-uProjection.x));
    vec3 center=vec3((uControl.xy-.5)*vec2(5.6,3.2),0.);
    vec3 origin=worldToModel(vec3(0,0,uProjection.x)-center);
    vec3 rd=worldToModel(ray);
    vec3 ro=origin/max(.08,mainScale());
    vec3 safeRd=mix(vec3(1.e-6),rd,greaterThan(abs(rd),vec3(1.e-6)));
    vec3 lo=(-vec3(2.95,2.95,.80)-ro)/safeRd;
    vec3 hi=( vec3(2.95,2.95,.80)-ro)/safeRd;
    vec3 nearT=min(lo,hi),farT=max(lo,hi);
    float a=max(0.,max(nearT.x,max(nearT.y,nearT.z)));
    float b=min(farT.x,min(farT.y,farT.z));
    vec3 color=vec3(0.);float transmission=1.;
    if(b>a){
        float stepSize=(b-a)/float(VOLUME_STEPS);
        for(int i=0;i<VOLUME_STEPS;i++){
            vec4 material=medium(ro+rd*(a+(float(i)+.5)*stepSize));
            float opacity=1.-exp(-material.a*stepSize);
            float integral=material.a>.0001?opacity/material.a:stepSize;
            color+=transmission*material.rgb*integral;
            transmission*=1.-opacity;
        }
    }
    color+=surroundingClouds(origin/max(.08,outerScale()),rd);
    fragColor=TDOutputSwizzle(vec4(color,1.));
}
