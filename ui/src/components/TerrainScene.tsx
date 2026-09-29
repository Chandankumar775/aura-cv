import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * Ambient 3-D terrain: a displaced point field with topographic contour lines and a slow
 * sensor sweep, drawn from the subject's own world (aerial reconnaissance over terrain).
 * Bundled locally (no CDN). Respects prefers-reduced-motion (single static frame), pauses
 * when the tab is hidden, caps pixel ratio and frame rate so glass panels above stay smooth.
 */

const NOISE = /* glsl */ `
vec3 permute(vec3 x){return mod(((x*34.0)+1.0)*x,289.0);}
float snoise(vec2 v){
  const vec4 C=vec4(0.211324865405187,0.366025403784439,-0.577350269189626,0.024390243902439);
  vec2 i=floor(v+dot(v,C.yy)); vec2 x0=v-i+dot(i,C.xx);
  vec2 i1=(x0.x>x0.y)?vec2(1.0,0.0):vec2(0.0,1.0);
  vec4 x12=x0.xyxy+C.xxzz; x12.xy-=i1; i=mod(i,289.0);
  vec3 p=permute(permute(i.y+vec3(0.0,i1.y,1.0))+i.x+vec3(0.0,i1.x,1.0));
  vec3 m=max(0.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.0); m=m*m; m=m*m;
  vec3 x=2.0*fract(p*C.www)-1.0; vec3 h=abs(x)-0.5; vec3 ox=floor(x+0.5); vec3 a0=x-ox;
  m*=1.79284291400159-0.85373472095314*(a0*a0+h*h);
  vec3 g; g.x=a0.x*x0.x+h.x*x0.y; g.yz=a0.yz*x12.xz+h.yz*x12.yw; return 130.0*dot(m,g);
}
float fbm(vec2 p){float s=0.0,a=0.55;for(int i=0;i<5;i++){s+=a*snoise(p);p*=2.03;a*=0.5;}return s;}
`;

const VERT = /* glsl */ `
uniform float uTime; uniform float uAmp;
varying float vH; varying float vDepth; varying float vSweep; varying vec2 vXZ;
${NOISE}
void main(){
  vec3 p=position;
  vec2 q=p.xz*0.022+vec2(0.0,uTime*0.012);
  float h=fbm(q);
  float ridge=1.0-abs(snoise(q*0.6+3.7));
  h=h*0.8+ridge*0.45;
  p.y=h*uAmp;
  vH=h; vXZ=p.xz;
  vec4 mv=modelViewMatrix*vec4(p,1.0);
  vDepth=-mv.z;
  float sweepPos=mod(uTime*9.0,220.0)-110.0;
  vSweep=exp(-pow((p.x-sweepPos)/5.5,2.0));
  gl_PointSize=(1.6+vSweep*1.6)*(95.0/max(vDepth,1.0));
  gl_Position=projectionMatrix*mv;
}`;

const FRAG = /* glsl */ `
uniform vec3 uBase; uniform vec3 uHi; uniform vec3 uSweep; uniform float uIntensity;
varying float vH; varying float vDepth; varying float vSweep; varying vec2 vXZ;
void main(){
  vec2 c=gl_PointCoord-0.5; if(dot(c,c)>0.25) discard;
  float band=fract(vH*7.0);
  float contour=smoothstep(0.10,0.0,abs(band-0.5)-0.40);
  float fog=smoothstep(170.0,25.0,vDepth);
  float edge=smoothstep(95.0,55.0,abs(vXZ.x));
  vec3 col=mix(uBase,uHi,clamp(vH*0.6+0.5,0.0,1.0));
  col=mix(col,uSweep,vSweep*0.85);
  float a=(0.10+contour*0.55+vSweep*0.55)*fog*edge*uIntensity;
  gl_FragColor=vec4(col,a);
}`;

export default function TerrainScene({ intensity = 1, className = "" }: { intensity?: number; className?: string }) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: "low-power" });
    } catch {
      return; // no WebGL: the CSS ground underneath still carries the page
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(52, 1, 0.5, 400);
    camera.position.set(0, 26, 92);
    camera.lookAt(0, 0, -10);

    const geo = new THREE.PlaneGeometry(220, 220, 190, 190);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 18 },
        uAmp: { value: 13 },
        uIntensity: { value: intensity },
        uBase: { value: new THREE.Color("#35527a") },
        uHi: { value: new THREE.Color("#8db7ff") },
        uSweep: { value: new THREE.Color("#b9f0dc") },
      },
    });
    const points = new THREE.Points(geo, mat);
    scene.add(points);

    const resize = () => {
      const w = el.clientWidth || window.innerWidth;
      const h = el.clientHeight || window.innerHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    let raf = 0;
    let last = 0;
    let t = 18;
    const pointer = { x: 0, y: 0 };
    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX / window.innerWidth - 0.5;
      pointer.y = e.clientY / window.innerHeight - 0.5;
    };
    window.addEventListener("pointermove", onMove, { passive: true });

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden || now - last < 33) return; // ~30 fps is plenty for ambience
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      t += dt;
      mat.uniforms.uTime.value = t;
      camera.position.x += (pointer.x * 10 - camera.position.x) * 0.02;
      camera.position.y += (26 - pointer.y * 6 - camera.position.y) * 0.02;
      camera.lookAt(0, 0, -10);
      renderer.render(scene, camera);
    };
    if (reduce) renderer.render(scene, camera);
    else raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      geo.dispose();
      mat.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [intensity]);

  return <div ref={host} aria-hidden className={`pointer-events-none fixed inset-0 ${className}`} />;
}
