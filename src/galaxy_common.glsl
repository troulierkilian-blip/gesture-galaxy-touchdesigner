// Shared by point generation and volume evaluation; angles are radians.
uniform vec4 uMotion;
uniform vec4 uControl;
uniform vec4 uView;
uniform vec4 uProjection; // camera Z, view width at Z=0, view height, reserved
const float TAU=6.28318530718;
const float REST_SPREAD=.7655;
const float DISK_RADIUS_GAIN=1.10;
float hash(float x){return fract(sin(x*127.1+311.7)*43758.5453);}
float hash31(vec3 p){
    p=fract(p*.1031);p+=dot(p,p.yzx+33.33);
    return fract((p.x+p.y)*p.z);
}
float noise3(vec3 p){
    vec3 a=floor(p),f=fract(p);f=f*f*(3.-2.*f);
    return mix(mix(mix(hash31(a),hash31(a+vec3(1,0,0)),f.x),
                   mix(hash31(a+vec3(0,1,0)),hash31(a+vec3(1,1,0)),f.x),f.y),
               mix(mix(hash31(a+vec3(0,0,1)),hash31(a+vec3(1,0,1)),f.x),
                   mix(hash31(a+vec3(0,1,1)),hash31(a+vec3(1,1,1)),f.x),f.y),f.z);
}
float cloudNoise(vec3 p){return .57*noise3(p)+.28*noise3(p*2.07+3.1)+.15*noise3(p*4.13+7.7);}
mat2 turn(float a){return mat2(cos(a),sin(a),-sin(a),cos(a));}
vec3 modelToWorld(vec3 p){
    p.xy=turn(uView.z)*p.xy;p.yz=turn(uView.y)*p.yz;
    p.xz=turn(-uView.x)*p.xz;p.xy=turn(-.22)*p.xy;
    return p;
}
vec3 worldToModel(vec3 p){
    p.xy=turn(.22)*p.xy;p.xz=turn(uView.x)*p.xz;
    p.yz=turn(-uView.y)*p.yz;p.xy=turn(-uView.z)*p.xy;
    return p;
}
float mainScale(){return mix(.23,1.42,uMotion.y)*uMotion.z;}
float outerScale(){return max(REST_SPREAD,mix(.23,1.42,uMotion.y))*uMotion.z;}
float spiralAngle(float r){return 2.75*log(1.+r*1.8)+.085*sin(r*4.1)+.035*sin(r*11.3);}
float branchAngle(float r){return .13+.14*smoothstep(.6,1.8,r);}
float branchWindow(float r){return smoothstep(.45,.85,r)*(1.-smoothstep(1.8,2.3,r));}
float diskWarp(vec2 p){return .033*sin(p.x*2.3)*cos(p.y*1.7);}
float dustField(vec3 p){
    float r=length(p.xy),phase=atan(p.y,p.x)-spiralAngle(r);
    float lane=pow(.5+.5*cos(4.*(phase+.095)),30.);
    return lane*smoothstep(.40,.70,cloudNoise(p*vec3(5.,5.,9.)))*smoothstep(.25,.65,r);
}
vec3 coolColor(){
    if(uControl.w>1.5)return vec3(.85,.47,.18);
    if(uControl.w>.5)return vec3(.18,.64,.80);
    return vec3(.34,.47,.90);
}
vec3 accentColor(){
    if(uControl.w>1.5)return vec3(.70,.28,.16);
    if(uControl.w>.5)return vec3(.26,.39,.80);
    return vec3(.54,.30,.72);
}
vec3 clusterCenter(int i){
    if(i==0)return vec3(-3.55,.55,.15);
    if(i==1)return vec3(3.35,-.35,-.30);
    if(i==2)return vec3(-2.25,2.05,-.42);
    if(i==3)return vec3(2.50,1.95,.30);
    if(i==4)return vec3(-2.55,-1.85,.42);
    if(i==5)return vec3(2.40,-2.00,-.30);
    if(i==6)return vec3(-.45,2.65,.80);
    return vec3(.75,-2.75,-.75);
}
float clusterRadius(int i){return .115+.075*hash(float(i)+21.73);}
vec3 clusterColor(int i){return mix(coolColor(),vec3(.93,.80,.62),.22+.28*hash(float(i)+7.2));}
