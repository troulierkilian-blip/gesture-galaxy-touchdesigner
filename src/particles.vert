// @include galaxy_common.glsl
out vec4 vParticle;
void main(){
    vec3 seed=TDPos();
    float index=floor(seed.z*20000.);
    float h=hash(index),h2=hash(index+193.7),h3=hash(index+319.3);
    float slot=mod(index,20.);
    vec3 pos,color;
    float brightness,pointSize;
    // 10% stable sky, 25% surrounding clusters, 65% the main galaxy.
    if(slot<2.){
        pos=vec3((seed.x-.5)*10.,(seed.y-.5)*6.,-1.-h*3.5);
        color=mix(vec3(.48,.62,.9),vec3(1.,.86,.68),h2);
        brightness=(.035+.17*pow(h,3.))*(.94+.06*sin(uMotion.x*.55+h2*50.));
        pointSize=1.+2.2*pow(h3,14.);
    }else if(slot<7.){
        int group=int(mod(floor(index/20.)*5.+slot-2.,8.));
        float a=TAU*seed.y;
        vec3 normal=vec3(sqrt(-2.*log(max(seed.x,.002)))*vec2(cos(a),sin(a)),
            sqrt(-2.*log(max(h2,.002)))*cos(TAU*h3));
        normal=clamp(normal,vec3(-2.8),vec3(2.8));
        float radius=clusterRadius(group)*(h<.78?.78:2.3);
        vec3 center=clusterCenter(group);
        vec3 offset=normal*radius*vec3(1.,.75,.85);
        offset.xy=turn(float(group)*.7)*offset.xy;
        pos=modelToWorld(center+offset)*outerScale();
        pos.xy+=(uControl.xy-.5)*vec2(5.6,3.2);
        color=mix(clusterColor(group),vec3(.94,.96,1.),.38*h3);
        brightness=(.11+.48*pow(h3,3.))*(1.+uMotion.w*.12);
        pointSize=1.+1.65*pow(h2,9.);
    }else{
        float r,theta,z;
        if(h<.23){
            r=.62*pow(seed.x,1.65);
            theta=TAU*seed.y;
            z=(h2-.5)*.56*exp(-r*2.6);
        }else if(h<.94){
            r=.16+2.30*pow(seed.x,.78);
            float arm=mod(floor(index/20.)+slot,4.);
            float branch=step(.68,h3)*branchWindow(r);
            float scatter=(h2+h3-1.)*(.13+.12*r);
            theta=arm*TAU*.25+spiralAngle(r)+branch*branchAngle(r)+scatter;
            z=(seed.y-.5)*(.07+.18*r);
        }else{
            r=.3+2.2*sqrt(seed.x);theta=TAU*seed.y;z=(h2-.5)*1.0;
        }
        vec3 local=vec3(r*cos(theta),r*sin(theta),z);
        local.z+=diskWarp(local.xy);
        float knots=cloudNoise(local*vec3(4.,4.,6.));
        float dust=dustField(local);
        pos=local;pos.xy*=DISK_RADIUS_GAIN;
        pos=modelToWorld(pos)*mainScale();
        pos.xy+=(uControl.xy-.5)*vec2(5.6,3.2);
        vec3 armColor=mix(coolColor(),accentColor(),h3);
        color=mix(vec3(1.,.85,.64),armColor,smoothstep(.18,.85,r));
        color=mix(color,vec3(.88,.92,1.),.28*h2);
        brightness=(.18+.62*pow(h3,3.))*(.70+.75*knots)*(1.-.64*dust);
        brightness*=1.+uMotion.w*.38;
        pointSize=1.05+1.85*pow(h2,7.);
    }
    gl_Position=TDWorldToProj(TDDeform(pos));
    if(index>=uControl.z)gl_Position=vec4(2.,2.,2.,1.);
    gl_PointSize=pointSize;
    vParticle=vec4(color*brightness,1.);
}
