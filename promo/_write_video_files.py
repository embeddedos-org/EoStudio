import json, os

base = '/home/spatchava/embeddedos-org/eostudio-promo-video'
os.makedirs(f'{base}/src', exist_ok=True)
os.makedirs(f'{base}/out', exist_ok=True)

pkg = {
    "name": "eostudio-promo-video",
    "version": "1.0.0",
    "type": "module",
    "scripts": {
        "studio": "remotion studio src/index.js",
        "render": "remotion render src/index.js EoStudioPromo out/eostudio-v1-promo.mp4"
    },
    "dependencies": {
        "@remotion/cli": "4.0.451",
        "@remotion/renderer": "4.0.451",
        "react": "^19.2.5",
        "react-dom": "^19.2.5",
        "remotion": "4.0.451"
    }
}
with open(f'{base}/package.json', 'w') as f:
    json.dump(pkg, f, indent=2)

with open(f'{base}/src/index.js', 'w') as f:
    f.write('import { registerRoot } from "remotion";\n')
    f.write('import { RemotionRoot } from "./Root";\n')
    f.write('registerRoot(RemotionRoot);\n')

with open(f'{base}/src/Root.jsx', 'w') as f:
    f.write('import { Composition } from "remotion";\n')
    f.write('import { EoStudioPromo } from "./EoStudioPromo";\n\n')
    f.write('export const RemotionRoot = () => {\n')
    f.write('  return (\n')
    f.write('    <Composition\n')
    f.write('      id="EoStudioPromo"\n')
    f.write('      component={EoStudioPromo}\n')
    f.write('      durationInFrames={450}\n')
    f.write('      fps={30}\n')
    f.write('      width={1920}\n')
    f.write('      height={1080}\n')
    f.write('    />\n')
    f.write('  );\n')
    f.write('};\n')

# Main video component
lines = []
lines.append('import {')
lines.append('  AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig,')
lines.append('  interpolate, spring,')
lines.append('} from "remotion";')
lines.append('')
lines.append('function FadeIn({ children, delay = 0, style = {} }) {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const opacity = interpolate(frame - delay, [0, 15], [0, 1], { extrapolateRight: "clamp" });')
lines.append('  const y = interpolate(frame - delay, [0, 15], [30, 0], { extrapolateRight: "clamp" });')
lines.append('  return <div style={{ opacity: Math.max(0, opacity), transform: `translateY(${Math.max(0,y)}px)`, ...style }}>{children}</div>;')
lines.append('}')
lines.append('')
lines.append('function ScaleIn({ children, delay = 0, style = {} }) {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const { fps } = useVideoConfig();')
lines.append('  const s = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 200 } });')
lines.append('  const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateRight: "clamp" });')
lines.append('  return <div style={{ transform: `scale(${s})`, opacity: Math.max(0, opacity), ...style }}>{children}</div>;')
lines.append('}')
lines.append('')
lines.append('const font = "Inter, system-ui, sans-serif";')
lines.append('const grad = (c) => ({ background: c, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" });')
lines.append('')

# Hero
lines.append('function HeroSlide() {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const { fps } = useVideoConfig();')
lines.append('  const s = spring({ frame, fps, config: { damping: 10, stiffness: 100 } });')
lines.append('  const glow = interpolate(frame, [0, 30, 60, 90], [0, 0.6, 0.3, 0.5]);')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "linear-gradient(135deg, #0f172a, #1e1b4b, #0f172a)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>')
lines.append('      <div style={{ position: "absolute", width: 600, height: 600, borderRadius: "50%", background: "radial-gradient(circle, rgba(99,102,241,0.3), transparent 70%)", opacity: glow, filter: "blur(60px)" }} />')
lines.append('      <div style={{ transform: `scale(${s})`, fontSize: 120, fontWeight: 900, fontFamily: font, ...grad("linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899)"), zIndex: 1 }}>EoStudio</div>')
lines.append('      <FadeIn delay={10} style={{ zIndex: 1 }}><div style={{ fontSize: 36, color: "#94a3b8", fontWeight: 500, fontFamily: font, marginTop: 12 }}>Design Everything.</div></FadeIn>')
lines.append('      <FadeIn delay={20} style={{ zIndex: 1 }}><div style={{ fontSize: 18, color: "#3b82f6", marginTop: 16, padding: "8px 24px", border: "1px solid #3b82f6", borderRadius: 24, fontFamily: font }}>v1.0.0 Community Edition</div></FadeIn>')
lines.append('      <FadeIn delay={30} style={{ zIndex: 1 }}><div style={{ fontSize: 20, color: "#64748b", marginTop: 28, textAlign: "center", maxWidth: 650, lineHeight: 1.7, fontFamily: font }}>13 editors. 33+ code generators. AI-powered. Animation engine. Prototyping. Video promos.</div></FadeIn>')
lines.append('    </AbsoluteFill>);')
lines.append('}')
lines.append('')

# Editors
lines.append('const editors = [')
lines.append('  {i:"\\u{1F3A8}",n:"3D"},{i:"\\u{1F4D0}",n:"CAD"},{i:"\\u{1F5BC}",n:"Image"},{i:"\\u{1F3AE}",n:"Game"},')
lines.append('  {i:"\\u{1F4F1}",n:"UI/UX"},{i:"\\u{1F3ED}",n:"Product"},{i:"\\u{1F3E0}",n:"Interior"},{i:"\\u{1F4CA}",n:"UML"},')
lines.append('  {i:"\\u{1F4C8}",n:"Sim"},{i:"\\u{1F5C4}",n:"Database"},{i:"\\u{1F527}",n:"Hardware"},{i:"\\u{1F4BB}",n:"IDE"},')
lines.append('  {i:"\\u{1F3AC}",n:"Promo",h:true},')
lines.append('];')
lines.append('')
lines.append('function EditorsSlide() {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const { fps } = useVideoConfig();')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "linear-gradient(180deg, #0f172a, #1a1a2e)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>')
lines.append('      <FadeIn><div style={{ fontSize: 56, fontWeight: 800, fontFamily: font, ...grad("linear-gradient(90deg, #3b82f6, #22d3ee)") }}>13 Design Editors</div></FadeIn>')
lines.append('      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 180px)", gap: 16, marginTop: 48 }}>')
lines.append('        {editors.map((ed, idx) => {')
lines.append('          const sc = spring({ frame: frame - idx * 3, fps, config: { damping: 15, stiffness: 200 } });')
lines.append('          const op = interpolate(frame - idx * 3, [0, 10], [0, 1], { extrapolateRight: "clamp" });')
lines.append('          return <div key={idx} style={{ background: ed.h ? "rgba(139,92,246,0.15)" : "rgba(255,255,255,0.05)", border: `1px solid ${ed.h ? "#8b5cf6" : "rgba(255,255,255,0.1)"}`, borderRadius: 14, padding: "18px 12px", textAlign: "center", transform: `scale(${sc})`, opacity: Math.max(0, op) }}>')
lines.append('            <div style={{ fontSize: 36 }}>{ed.i}</div>')
lines.append('            <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", marginTop: 6, fontFamily: font }}>{ed.n}</div>')
lines.append('          </div>;')
lines.append('        })}')
lines.append('      </div>')
lines.append('    </AbsoluteFill>);')
lines.append('}')
lines.append('')

# Animation
lines.append('const presets = ["fadeIn","fadeInUp","slideUp","scaleIn","popIn","bounceIn","pulse","shake","wobble","revealUp","spring:gentle","spring:wobbly","spring:stiff"];')
lines.append('')
lines.append('function AnimSlide() {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const bounceY = interpolate(frame % 30, [0, 7, 15, 22, 30], [0, -25, 0, -10, 0]);')
lines.append('  const pulseS = interpolate(frame % 40, [0, 20, 40], [1, 1.12, 1]);')
lines.append('  const shakeX = frame % 20 < 12 ? interpolate(frame % 20, [0,2,4,6,8,10,12], [0,-8,8,-8,8,-4,0]) : 0;')
lines.append('  const spinR = (frame * 4) % 360;')
lines.append('  const boxes = [{l:"Bounce",bg:"#3b82f6",t:`translateY(${bounceY}px)`},{l:"Pulse",bg:"#8b5cf6",t:`scale(${pulseS})`},{l:"Shake",bg:"#ec4899",t:`translateX(${shakeX}px)`},{l:"Spin",bg:"#22d3ee",t:`rotate(${spinR}deg)`}];')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "linear-gradient(135deg, #1a1a2e, #2d1b69)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>')
lines.append('      <FadeIn><div style={{ fontSize: 56, fontWeight: 800, fontFamily: font, ...grad("linear-gradient(90deg, #8b5cf6, #ec4899)") }}>Animation Engine</div></FadeIn>')
lines.append('      <FadeIn delay={5}><div style={{ fontSize: 20, color: "#c4b5fd", marginTop: 8, fontFamily: font }}>Spring physics \\u00B7 25 presets \\u00B7 Framer Motion + GSAP codegen</div></FadeIn>')
lines.append('      <div style={{ display: "flex", gap: 32, marginTop: 48 }}>')
lines.append('        {boxes.map((b,i) => <div key={i} style={{ width: 120, height: 120, borderRadius: 18, background: b.bg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, fontWeight: 700, color: "#fff", fontFamily: font, transform: b.t, boxShadow: `0 8px 32px ${b.bg}44` }}>{b.l}</div>)}')
lines.append('      </div>')
lines.append('      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 36, maxWidth: 750, justifyContent: "center" }}>')
lines.append('        {presets.map((p,i) => { const o = interpolate(frame - i * 2, [0, 8], [0, 1], { extrapolateRight: "clamp" }); return <span key={i} style={{ padding: "6px 14px", background: "rgba(139,92,246,0.2)", border: "1px solid rgba(139,92,246,0.3)", borderRadius: 20, fontSize: 13, color: "#c4b5fd", fontFamily: font, opacity: Math.max(0,o) }}>{p}</span>; })}')
lines.append('      </div>')
lines.append('    </AbsoluteFill>);')
lines.append('}')
lines.append('')

# AI
lines.append('const aiFeats = [{i:"\\u2728",t:"Text \\u2192 Animated UI",d:"Describe UI, get animated components"},{i:"\\u{1F4F8}",t:"Screenshot \\u2192 UI",d:"Upload screenshot, extract components"},{i:"\\u{1F3A8}",t:"AI Design System",d:"Generate tokens & palette from brand"},{i:"\\u267F",t:"A11y Audit",d:"WCAG 2.1 AA with fix suggestions"},{i:"\\u{1F9E9}",t:"Smart Layout",d:"AI-optimized per device"},{i:"\\u{1F3AF}",t:"Prototyping",d:"Gestures, state machines, HTML export"}];')
lines.append('')
lines.append('function AISlide() {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const { fps } = useVideoConfig();')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "linear-gradient(135deg, #0f172a, #1e3a5f)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>')
lines.append('      <FadeIn><div style={{ fontSize: 56, fontWeight: 800, fontFamily: font, ...grad("linear-gradient(90deg, #22d3ee, #3b82f6)") }}>AI-Powered Design</div></FadeIn>')
lines.append('      <FadeIn delay={5}><div style={{ fontSize: 20, color: "#94a3b8", marginTop: 8, fontFamily: font }}>Ollama (local) + OpenAI</div></FadeIn>')
lines.append('      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 240px)", gap: 20, marginTop: 40 }}>')
lines.append('        {aiFeats.map((f,i) => { const sc = spring({ frame: frame - i * 4, fps, config: { damping: 14, stiffness: 180 } }); return <div key={i} style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 18, padding: 24, textAlign: "center", transform: `scale(${sc})` }}>')
lines.append('          <div style={{ fontSize: 44 }}>{f.i}</div>')
lines.append('          <div style={{ fontSize: 17, fontWeight: 700, color: "#e2e8f0", marginTop: 10, fontFamily: font }}>{f.t}</div>')
lines.append('          <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 8, lineHeight: 1.5, fontFamily: font }}>{f.d}</div>')
lines.append('        </div>; })}')
lines.append('      </div>')
lines.append('    </AbsoluteFill>);')
lines.append('}')
lines.append('')

# CTA
lines.append('function CTASlide() {')
lines.append('  const frame = useCurrentFrame();')
lines.append('  const { fps } = useVideoConfig();')
lines.append('  const s = spring({ frame, fps, config: { damping: 8, stiffness: 80 } });')
lines.append('  const floatY = interpolate(frame % 60, [0, 30, 60], [0, -8, 0]);')
lines.append('  const stats = [{n:"13",l:"Editors"},{n:"33+",l:"Frameworks"},{n:"25",l:"Animations"},{n:"200+",l:"Tests"}];')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "linear-gradient(135deg, #1e1b4b, #3730a3, #1e1b4b)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>')
lines.append('      <div style={{ fontSize: 80, fontWeight: 900, fontFamily: font, ...grad("linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899, #f59e0b)"), transform: `scale(${s}) translateY(${floatY}px)` }}>Design Everything.</div>')
lines.append('      <FadeIn delay={10}><div style={{ fontSize: 28, color: "#94a3b8", marginTop: 12, fontFamily: font }}>Open Source \\u00B7 MIT License \\u00B7 Free Forever</div></FadeIn>')
lines.append('      <ScaleIn delay={20}><div style={{ marginTop: 36, padding: "18px 56px", background: "linear-gradient(135deg, #3b82f6, #8b5cf6)", borderRadius: 14, fontSize: 22, fontWeight: 700, color: "#fff", fontFamily: font, boxShadow: "0 16px 48px rgba(59,130,246,0.35)" }}>github.com/embeddedos-org/EoStudio</div></ScaleIn>')
lines.append('      <div style={{ display: "flex", gap: 56, marginTop: 56 }}>')
lines.append('        {stats.map((st,i) => { const sc = spring({ frame: frame - 20 - i * 5, fps, config: { damping: 12, stiffness: 150 } }); return <div key={i} style={{ textAlign: "center", transform: `scale(${sc})` }}><div style={{ fontSize: 56, fontWeight: 900, color: "#3b82f6", fontFamily: font }}>{st.n}</div><div style={{ fontSize: 16, color: "#64748b", marginTop: 4, fontFamily: font }}>{st.l}</div></div>; })}')
lines.append('      </div>')
lines.append('    </AbsoluteFill>);')
lines.append('}')
lines.append('')

# Main export
lines.append('export function EoStudioPromo() {')
lines.append('  return (')
lines.append('    <AbsoluteFill style={{ background: "#0a0a1a" }}>')
lines.append('      <Sequence from={0} durationInFrames={90}><HeroSlide /></Sequence>')
lines.append('      <Sequence from={90} durationInFrames={90}><EditorsSlide /></Sequence>')
lines.append('      <Sequence from={180} durationInFrames={90}><AnimSlide /></Sequence>')
lines.append('      <Sequence from={270} durationInFrames={90}><AISlide /></Sequence>')
lines.append('      <Sequence from={360} durationInFrames={90}><CTASlide /></Sequence>')
lines.append('    </AbsoluteFill>')
lines.append('  );')
lines.append('}')

with open(f'{base}/src/EoStudioPromo.jsx', 'w') as f:
    f.write('\n'.join(lines))

print('ALL FILES WRITTEN')
for fn in os.listdir(f'{base}/src'):
    fpath = f'{base}/src/{fn}'
    print(f'  {fn}: {os.path.getsize(fpath)} bytes')
print(f'  package.json: {os.path.getsize(f"{base}/package.json")} bytes')
