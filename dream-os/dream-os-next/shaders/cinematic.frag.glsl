precision highp float;
uniform vec2 u_res; uniform float u_time; uniform float u_intro;
float hash(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){
  vec2 i=floor(p), f=fract(p);
  float a=hash(i), b=hash(i+vec2(1.,0.)), c=hash(i+vec2(0.,1.)), d=hash(i+vec2(1.,1.));
  vec2 u=f*f*(3.0-2.0*f);
  return mix(a,b,u.x)+(c-a)*u.y*(1.0-u.x)+(d-b)*u.x*u.y;
}
float fbm(vec2 p){
  float v=0.0, a=0.5; mat2 m=mat2(1.6,1.2,-1.2,1.6);
  for(int i=0;i<4;i++){ v+=a*noise(p); p=m*p; a*=0.5; } return v;
}
float fbm3(vec2 p){
  float v=0.0, a=0.5; mat2 m=mat2(1.6,1.2,-1.2,1.6);
  for(int i=0;i<3;i++){ v+=a*noise(p); p=m*p; a*=0.5; } return v;
}
float field(vec2 p){
  float t = u_time*0.13;
  vec2 warp = vec2(fbm(p*1.5 + t), fbm(p*1.5 + vec2(5.2,1.3) - t));
  float n = fbm(p*2.0 + warp*2.8 + t*0.7);
  vec2 warp2 = vec2(fbm(p*3.0 + warp*1.5 + t*0.35), fbm(p*3.0 - warp*1.5 - t*0.25));
  float n2 = fbm(p*3.6 + warp2*3.4);
  float neb = n*0.62 + n2*0.38;
  float band = sin(p.y*3.0 + fbm(p*1.2 + t*0.5)*2.2 + u_time*0.40);
  band = smoothstep(0.5,1.0,band)*0.5;
  return neb + band;
}
vec3 shade(float neb, vec2 p){
  vec3 c1=vec3(0.02,0.03,0.08);
  vec3 c2=vec3(0.20,0.10,0.50);
  vec3 c3=vec3(0.55,0.28,0.95);
  vec3 c4=vec3(0.96,0.82,1.0);
  vec3 col = mix(c1,c2, smoothstep(0.16,0.46,neb));
  col = mix(col,c3, smoothstep(0.50,0.76,neb));
  col = mix(col,c4, smoothstep(0.82,0.97,neb));
  float fil = smoothstep(0.78,0.93,neb); col += fil*vec3(0.5,0.24,0.7);
  float deep = smoothstep(0.0,0.16,neb)*(1.0-smoothstep(0.16,0.45,neb));
  col += deep*0.05*vec3(0.15,0.5,0.75);
  float ang = atan(p.y, p.x);
  float ray = 0.5+0.5*sin(ang*9.0 + u_time*0.55 + neb*4.0);
  ray = pow(ray,4.0);
  float center = smoothstep(0.95,0.0,length(p));
  col += ray*center*0.12*vec3(0.7,0.55,1.0);
  return col;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  float aspect = u_res.x/u_res.y;
  vec2 p = (uv-0.5); p.x*=aspect;
  float zoom = 1.0 + 0.12*sin(u_time*0.13) + (1.0-u_intro)*1.6;
  p /= zoom;
  float t = u_time*0.13;
  float far = fbm3(p*0.7 + t*0.4);
  far = smoothstep(0.35,0.9,far)*0.45;
  float pl = length(p);
  vec2 dir = pl>1e-4 ? p/pl : vec2(0.0);
  float ca = 0.012 * pl;
  float heroC = field(p);
  float heroR = field(p + dir*ca);
  float heroB = field(p - dir*ca);
  vec3 col = vec3(shade(heroR+far,p).r, shade(heroC+far,p).g, shade(heroB+far,p).b);
  float occ = smoothstep(0.55,0.78, fbm(p*2.6 + t*0.6));
  col *= 1.0 - occ*0.38;
  col *= smoothstep(1.4,0.25,pl);
  col = 1.0 - exp(-col*1.5);
  col *= u_intro;
  col += (hash(uv*u_res + fract(u_time)*97.0)-0.5)*0.022;
  gl_FragColor = vec4(col,1.0);
}