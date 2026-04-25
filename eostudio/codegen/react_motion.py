"""React Animation code generator — Framer Motion and GSAP output from EoStudio animation data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from eostudio.core.animation.keyframe import EasingFunction
from eostudio.core.animation.timeline import AnimationClip, AnimationTimeline
from eostudio.core.animation.presets import AnimationPreset, PRESETS


class ReactMotionGenerator:
    """Generates React code with Framer Motion or GSAP animations from EoStudio animation data.

    Supports:
    - Framer Motion: <motion.div>, AnimatePresence, useAnimation, layout animations
    - GSAP: gsap.timeline(), ScrollTrigger, stagger animations
    - CSS @keyframes as fallback
    """

    def __init__(self, library: str = "framer-motion") -> None:
        """Initialize with target animation library.

        Args:
            library: "framer-motion", "gsap", or "css"
        """
        self.library = library

    def generate(self, timeline: AnimationTimeline,
                 components: List[Dict[str, Any]],
                 screens: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """Generate React source files with animation code.

        Returns mapping of filename -> source code.
        """
        if self.library == "framer-motion":
            return self._generate_framer_motion(timeline, components, screens)
        elif self.library == "gsap":
            return self._generate_gsap(timeline, components, screens)
        else:
            return self._generate_css_animations(timeline, components, screens)

    # ------------------------------------------------------------------
    # Framer Motion generation
    # ------------------------------------------------------------------

    def _generate_framer_motion(self, timeline: AnimationTimeline,
                                 components: List[Dict[str, Any]],
                                 screens: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
        files: Dict[str, str] = {}

        files["src/App.jsx"] = self._fm_app(screens or [{"name": "Home", "components": components}])
        files["src/index.jsx"] = self._fm_index()
        files["src/hooks/useAnimation.js"] = self._fm_use_animation_hook()
        files["src/hooks/useScrollAnimation.js"] = self._fm_scroll_animation_hook()
        files["src/components/AnimatedComponent.jsx"] = self._fm_animated_component()
        files["src/components/PageTransition.jsx"] = self._fm_page_transition()
        files["src/animations/presets.js"] = self._fm_presets()
        files["src/animations/variants.js"] = self._fm_variants(timeline)
        files["package.json"] = self._package_json("framer-motion")

        screens_list = screens or [{"name": "Home", "components": components}]
        for screen in screens_list:
            name = self._component_name(screen.get("name", "Home"))
            screen_clips = [c for c in timeline.clips if c.target_id.startswith(name.lower())]
            files[f"src/screens/{name}.jsx"] = self._fm_screen(name, screen.get("components", components), screen_clips)
            files[f"src/screens/{name}.module.css"] = self._fm_screen_css(name)

        return files

    def _fm_index(self) -> str:
        return (
            "import React from 'react';\n"
            "import ReactDOM from 'react-dom/client';\n"
            "import { BrowserRouter } from 'react-router-dom';\n"
            "import App from './App';\n"
            "import './index.css';\n\n"
            "const root = ReactDOM.createRoot(document.getElementById('root'));\n"
            "root.render(\n"
            "  <React.StrictMode>\n"
            "    <BrowserRouter>\n"
            "      <App />\n"
            "    </BrowserRouter>\n"
            "  </React.StrictMode>\n"
            ");\n"
        )

    def _fm_app(self, screens: List[Dict[str, Any]]) -> str:
        imports = ["import React from 'react';",
                   "import { Routes, Route, Link, useLocation } from 'react-router-dom';",
                   "import { AnimatePresence } from 'framer-motion';",
                   "import PageTransition from './components/PageTransition';"]

        routes = []
        nav_links = []
        for i, screen in enumerate(screens):
            name = self._component_name(screen.get("name", "Home"))
            path = "/" if i == 0 else f"/{self._kebab(screen.get('name', 'home'))}"
            imports.append(f"import {name} from './screens/{name}';")
            routes.append(f'          <Route path="{path}" element={{<PageTransition><{name} /></PageTransition>}} />')
            nav_links.append(f'        <Link to="{path}">{screen.get("name", "Home")}</Link>')

        return "\n".join(imports) + "\n\n" + (
            "function App() {\n"
            "  const location = useLocation();\n"
            "  return (\n"
            "    <div className=\"app\">\n"
            "      <nav className=\"app-nav\">\n"
            + "\n".join(nav_links) + "\n"
            "      </nav>\n"
            "      <main className=\"app-main\">\n"
            "        <AnimatePresence mode=\"wait\">\n"
            "          <Routes location={location} key={location.pathname}>\n"
            + "\n".join(routes) + "\n"
            "          </Routes>\n"
            "        </AnimatePresence>\n"
            "      </main>\n"
            "    </div>\n"
            "  );\n"
            "}\n\n"
            "export default App;\n"
        )

    def _fm_animated_component(self) -> str:
        return (
            "import React from 'react';\n"
            "import { motion } from 'framer-motion';\n"
            "import { presets } from '../animations/presets';\n\n"
            "/**\n"
            " * AnimatedComponent — wraps any child with motion animations.\n"
            " * @param {string} preset - Animation preset name (fadeIn, slideUp, etc.)\n"
            " * @param {number} delay - Animation delay in seconds\n"
            " * @param {number} duration - Animation duration in seconds\n"
            " * @param {string} trigger - 'mount' | 'scroll' | 'hover'\n"
            " * @param {object} custom - Custom Framer Motion variants\n"
            " */\n"
            "export default function AnimatedComponent({\n"
            "  children, preset = 'fadeIn', delay = 0, duration = 0.5,\n"
            "  trigger = 'mount', custom, className, style, ...props\n"
            "}) {\n"
            "  const animation = custom || presets[preset] || presets.fadeIn;\n"
            "  const variants = {\n"
            "    hidden: animation.initial,\n"
            "    visible: {\n"
            "      ...animation.animate,\n"
            "      transition: { duration, delay, ease: animation.ease || [0.25, 0.1, 0.25, 1] },\n"
            "    },\n"
            "  };\n\n"
            "  const motionProps = trigger === 'scroll'\n"
            "    ? { initial: 'hidden', whileInView: 'visible', viewport: { once: true, margin: '-100px' } }\n"
            "    : trigger === 'hover'\n"
            "    ? { initial: 'visible', whileHover: animation.hover || { scale: 1.05 } }\n"
            "    : { initial: 'hidden', animate: 'visible' };\n\n"
            "  return (\n"
            "    <motion.div\n"
            "      variants={variants}\n"
            "      {...motionProps}\n"
            "      className={className}\n"
            "      style={style}\n"
            "      {...props}\n"
            "    >\n"
            "      {children}\n"
            "    </motion.div>\n"
            "  );\n"
            "}\n"
        )

    def _fm_page_transition(self) -> str:
        return (
            "import React from 'react';\n"
            "import { motion } from 'framer-motion';\n\n"
            "const pageVariants = {\n"
            "  initial: { opacity: 0, y: 20 },\n"
            "  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] } },\n"
            "  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },\n"
            "};\n\n"
            "export default function PageTransition({ children }) {\n"
            "  return (\n"
            "    <motion.div\n"
            "      variants={pageVariants}\n"
            "      initial=\"initial\"\n"
            "      animate=\"animate\"\n"
            "      exit=\"exit\"\n"
            "    >\n"
            "      {children}\n"
            "    </motion.div>\n"
            "  );\n"
            "}\n"
        )

    def _fm_use_animation_hook(self) -> str:
        return (
            "import { useAnimation, useInView } from 'framer-motion';\n"
            "import { useRef, useEffect } from 'react';\n\n"
            "/**\n"
            " * useScrollAnimation — trigger animation when element scrolls into view.\n"
            " * @param {object} options - { threshold, once, rootMargin }\n"
            " * @returns {{ ref, controls, inView }}\n"
            " */\n"
            "export function useScrollAnimation(options = {}) {\n"
            "  const ref = useRef(null);\n"
            "  const controls = useAnimation();\n"
            "  const inView = useInView(ref, {\n"
            "    once: options.once ?? true,\n"
            "    margin: options.rootMargin ?? '-100px',\n"
            "  });\n\n"
            "  useEffect(() => {\n"
            "    if (inView) controls.start('visible');\n"
            "  }, [controls, inView]);\n\n"
            "  return { ref, controls, inView };\n"
            "}\n\n"
            "/**\n"
            " * useStaggerAnimation — stagger children animations.\n"
            " * @param {number} count - Number of children\n"
            " * @param {number} staggerDelay - Delay between each child\n"
            " */\n"
            "export function useStaggerAnimation(count, staggerDelay = 0.1) {\n"
            "  const controls = useAnimation();\n\n"
            "  const start = async () => {\n"
            "    await controls.start(i => ({\n"
            "      opacity: 1, y: 0,\n"
            "      transition: { delay: i * staggerDelay, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] },\n"
            "    }));\n"
            "  };\n\n"
            "  return { controls, start };\n"
            "}\n"
        )

    def _fm_scroll_animation_hook(self) -> str:
        return (
            "import { useScroll, useTransform, useSpring } from 'framer-motion';\n"
            "import { useRef } from 'react';\n\n"
            "/**\n"
            " * useParallax — parallax scrolling effect.\n"
            " * @param {number} speed - Parallax speed multiplier\n"
            " */\n"
            "export function useParallax(speed = 0.5) {\n"
            "  const ref = useRef(null);\n"
            "  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });\n"
            "  const y = useTransform(scrollYProgress, [0, 1], [speed * 100, -speed * 100]);\n"
            "  const smoothY = useSpring(y, { stiffness: 100, damping: 30 });\n"
            "  return { ref, y: smoothY };\n"
            "}\n\n"
            "/**\n"
            " * useScrollProgress — track scroll progress within an element.\n"
            " */\n"
            "export function useScrollProgress() {\n"
            "  const ref = useRef(null);\n"
            "  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });\n"
            "  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0, 1, 1, 0]);\n"
            "  const scale = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0.8, 1, 1, 0.8]);\n"
            "  return { ref, scrollYProgress, opacity, scale };\n"
            "}\n"
        )

    def _fm_presets(self) -> str:
        lines = ["// EoStudio Animation Presets for Framer Motion\n"]
        lines.append("export const presets = {")

        preset_map = {
            "fadeIn": {"initial": {"opacity": 0}, "animate": {"opacity": 1}},
            "fadeInUp": {"initial": {"opacity": 0, "y": 30}, "animate": {"opacity": 1, "y": 0}},
            "fadeInDown": {"initial": {"opacity": 0, "y": -30}, "animate": {"opacity": 1, "y": 0}},
            "fadeInLeft": {"initial": {"opacity": 0, "x": -30}, "animate": {"opacity": 1, "x": 0}},
            "fadeInRight": {"initial": {"opacity": 0, "x": 30}, "animate": {"opacity": 1, "x": 0}},
            "slideUp": {"initial": {"y": 100, "opacity": 0}, "animate": {"y": 0, "opacity": 1}},
            "slideDown": {"initial": {"y": -100, "opacity": 0}, "animate": {"y": 0, "opacity": 1}},
            "scaleIn": {"initial": {"scale": 0, "opacity": 0}, "animate": {"scale": 1, "opacity": 1}},
            "popIn": {"initial": {"scale": 0.5, "opacity": 0}, "animate": {"scale": 1, "opacity": 1},
                      "ease": [0.175, 0.885, 0.32, 1.275]},
            "bounceIn": {"initial": {"scale": 0.3, "opacity": 0},
                         "animate": {"scale": 1, "opacity": 1},
                         "ease": [0.68, -0.55, 0.265, 1.55]},
            "rotateIn": {"initial": {"rotate": -180, "opacity": 0}, "animate": {"rotate": 0, "opacity": 1}},
            "spin": {"initial": {"rotate": 0}, "animate": {"rotate": 360}},
            "pulse": {"animate": {"scale": [1, 1.05, 1]}, "transition": {"repeat": "Infinity", "duration": 2}},
            "shake": {"animate": {"x": [0, -10, 10, -10, 10, -5, 0]}, "transition": {"duration": 0.6}},
            "bounce": {"animate": {"y": [0, -20, 0, -8, 0]}, "transition": {"duration": 0.8}},
            "flash": {"animate": {"opacity": [1, 0, 1, 0, 1]}, "transition": {"duration": 1}},
            "revealUp": {"initial": {"opacity": 0, "y": 60}, "animate": {"opacity": 1, "y": 0}},
            "revealScale": {"initial": {"opacity": 0, "scale": 0.8}, "animate": {"opacity": 1, "scale": 1}},
        }

        for name, config in preset_map.items():
            lines.append(f"  {name}: {{")
            for key, val in config.items():
                lines.append(f"    {key}: {self._js_value(val)},")
            lines.append("  },")

        lines.append("};")
        lines.append("")
        lines.append("export const springConfigs = {")
        lines.append("  default: { type: 'spring', stiffness: 100, damping: 10, mass: 1 },")
        lines.append("  gentle: { type: 'spring', stiffness: 120, damping: 14, mass: 1 },")
        lines.append("  wobbly: { type: 'spring', stiffness: 180, damping: 12, mass: 1 },")
        lines.append("  stiff: { type: 'spring', stiffness: 300, damping: 20, mass: 1 },")
        lines.append("  slow: { type: 'spring', stiffness: 50, damping: 15, mass: 1 },")
        lines.append("  molasses: { type: 'spring', stiffness: 30, damping: 20, mass: 1 },")
        lines.append("};")

        return "\n".join(lines) + "\n"

    def _fm_variants(self, timeline: AnimationTimeline) -> str:
        lines = ["// Auto-generated animation variants from EoStudio timeline\n",
                 "import { presets } from './presets';\n"]
        lines.append("export const timelineVariants = {")

        for clip in timeline.clips:
            lines.append(f"  '{clip.target_id}': {{")
            initial: Dict[str, Any] = {}
            animate: Dict[str, Any] = {}
            for track in clip.tracks:
                if track.keyframes:
                    prop = self._to_motion_prop(track.property_name)
                    initial[prop] = track.keyframes[0].value
                    animate[prop] = track.keyframes[-1].value
            lines.append(f"    initial: {self._js_value(initial)},")
            lines.append(f"    animate: {self._js_value(animate)},")
            lines.append(f"    transition: {{ duration: {clip.duration}, delay: {clip.delay} }},")
            lines.append("  },")

        lines.append("};")
        lines.append("")
        lines.append("export const staggerContainer = {")
        lines.append("  hidden: { opacity: 0 },")
        lines.append("  visible: {")
        lines.append("    opacity: 1,")
        lines.append("    transition: { staggerChildren: 0.1, delayChildren: 0.2 },")
        lines.append("  },")
        lines.append("};")
        lines.append("")
        lines.append("export const staggerItem = {")
        lines.append("  hidden: { opacity: 0, y: 20 },")
        lines.append("  visible: { opacity: 1, y: 0 },")
        lines.append("};")

        return "\n".join(lines) + "\n"

    def _fm_screen(self, name: str, components: List[Dict[str, Any]],
                   clips: List[AnimationClip]) -> str:
        lines = [
            "import React from 'react';",
            "import { motion } from 'framer-motion';",
            "import AnimatedComponent from '../components/AnimatedComponent';",
            "import { staggerContainer, staggerItem } from '../animations/variants';",
            f"import styles from './{name}.module.css';",
            "",
            f"export default function {name}() {{",
            "  return (",
            f"    <motion.div className={{styles.screen}} variants={{staggerContainer}} initial=\"hidden\" animate=\"visible\">",
            f"      <h1>{name}</h1>",
        ]

        for i, comp in enumerate(components):
            comp_type = comp.get("type", "div")
            label = comp.get("label", comp.get("text", ""))
            preset = "fadeInUp"  # default
            delay = i * 0.1

            # Find matching clip for this component
            comp_id = comp.get("id", f"comp_{i}")
            for clip in clips:
                if clip.target_id == comp_id:
                    preset = clip.label or "fadeInUp"
                    delay = clip.delay
                    break

            if comp_type == "Button":
                lines.append(f"      <AnimatedComponent preset=\"{preset}\" delay={{{delay}}}>")
                lines.append(f"        <motion.button className={{styles.button}} whileHover={{{{ scale: 1.05 }}}} whileTap={{{{ scale: 0.95 }}}}>{label}</motion.button>")
                lines.append("      </AnimatedComponent>")
            elif comp_type == "Input":
                lines.append(f"      <AnimatedComponent preset=\"{preset}\" delay={{{delay}}}>")
                lines.append(f'        <input className={{styles.input}} placeholder="{label}" />')
                lines.append("      </AnimatedComponent>")
            elif comp_type == "Card":
                lines.append(f"      <AnimatedComponent preset=\"{preset}\" delay={{{delay}}}>")
                lines.append(f"        <motion.div className={{styles.card}} whileHover={{{{ y: -4, boxShadow: '0 10px 30px rgba(0,0,0,0.1)' }}}}>{label}</motion.div>")
                lines.append("      </AnimatedComponent>")
            elif comp_type == "Image":
                src = comp.get("src", "")
                lines.append(f"      <AnimatedComponent preset=\"{preset}\" delay={{{delay}}}>")
                lines.append(f'        <img className={{styles.image}} src="{src}" alt="{label}" />')
                lines.append("      </AnimatedComponent>")
            else:
                lines.append(f"      <AnimatedComponent preset=\"{preset}\" delay={{{delay}}}>")
                lines.append(f"        <p>{label}</p>")
                lines.append("      </AnimatedComponent>")

        lines.extend([
            "    </motion.div>",
            "  );",
            "}",
        ])
        return "\n".join(lines) + "\n"

    def _fm_screen_css(self, name: str) -> str:
        return (
            f"/* {name} screen styles — EoStudio Generated */\n"
            ".screen { display: flex; flex-direction: column; gap: 16px; padding: 24px; }\n"
            ".button {\n"
            "  padding: 12px 24px; border: none; border-radius: 8px;\n"
            "  background: #2563eb; color: #fff; font-size: 16px;\n"
            "  font-weight: 600; cursor: pointer;\n"
            "}\n"
            ".input {\n"
            "  width: 100%; padding: 12px 16px;\n"
            "  border: 1px solid #e5e7eb; border-radius: 8px; font-size: 16px;\n"
            "  transition: border-color 0.2s, box-shadow 0.2s;\n"
            "}\n"
            ".input:focus {\n"
            "  outline: none; border-color: #2563eb;\n"
            "  box-shadow: 0 0 0 3px rgba(37,99,235,0.1);\n"
            "}\n"
            ".card {\n"
            "  background: #fff; border-radius: 12px; padding: 20px;\n"
            "  box-shadow: 0 2px 8px rgba(0,0,0,0.08);\n"
            "  transition: box-shadow 0.3s;\n"
            "}\n"
            ".image { max-width: 100%; border-radius: 12px; }\n"
        )

    # ------------------------------------------------------------------
    # GSAP generation
    # ------------------------------------------------------------------

    def _generate_gsap(self, timeline: AnimationTimeline,
                       components: List[Dict[str, Any]],
                       screens: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
        files: Dict[str, str] = {}

        files["src/animations/gsapTimeline.js"] = self._gsap_timeline(timeline)
        files["src/hooks/useGSAP.js"] = self._gsap_hook()
        files["src/hooks/useScrollTrigger.js"] = self._gsap_scroll_trigger()
        files["package.json"] = self._package_json("gsap")

        screens_list = screens or [{"name": "Home", "components": components}]
        for screen in screens_list:
            name = self._component_name(screen.get("name", "Home"))
            files[f"src/screens/{name}.jsx"] = self._gsap_screen(name, screen.get("components", components), timeline)

        return files

    def _gsap_timeline(self, timeline: AnimationTimeline) -> str:
        lines = [
            "import gsap from 'gsap';",
            "import { ScrollTrigger } from 'gsap/ScrollTrigger';",
            "",
            "gsap.registerPlugin(ScrollTrigger);",
            "",
            "/**",
            " * Create the master timeline from EoStudio animation data.",
            " */",
            f"export function createTimeline(container) {{",
            f"  const tl = gsap.timeline({{ defaults: {{ ease: 'power2.out' }} }});",
            "",
        ]

        for clip in timeline.clips:
            target = f".{clip.target_id}"
            props: Dict[str, Any] = {}
            for track in clip.tracks:
                if track.keyframes and len(track.keyframes) >= 2:
                    prop = self._to_gsap_prop(track.property_name)
                    props[prop] = track.keyframes[-1].value

            props_str = ", ".join(f"{k}: {self._js_value(v)}" for k, v in props.items())
            position = f'"-={max(0, clip.duration - 0.1)}"' if clip.delay > 0 else ""
            lines.append(f"  tl.to('{target}', {{ {props_str}, duration: {clip.duration} }}{', ' + position if position else ''});")

        lines.append("")
        lines.append("  return tl;")
        lines.append("}")
        lines.append("")
        lines.append("/**")
        lines.append(" * Create scroll-triggered animations.")
        lines.append(" */")
        lines.append("export function createScrollAnimations(elements) {")
        lines.append("  elements.forEach((el, i) => {")
        lines.append("    gsap.from(el, {")
        lines.append("      y: 60, opacity: 0, duration: 0.8, delay: i * 0.1,")
        lines.append("      ease: 'power3.out',")
        lines.append("      scrollTrigger: {")
        lines.append("        trigger: el, start: 'top 80%', end: 'bottom 20%',")
        lines.append("        toggleActions: 'play none none reverse',")
        lines.append("      },")
        lines.append("    });")
        lines.append("  });")
        lines.append("}")
        lines.append("")
        lines.append("export function stagger(targets, props, staggerAmount = 0.1) {")
        lines.append("  return gsap.from(targets, { ...props, stagger: staggerAmount });")
        lines.append("}")

        return "\n".join(lines) + "\n"

    def _gsap_hook(self) -> str:
        return (
            "import { useRef, useEffect } from 'react';\n"
            "import gsap from 'gsap';\n\n"
            "export function useGSAP(animation, deps = []) {\n"
            "  const ref = useRef(null);\n"
            "  useEffect(() => {\n"
            "    if (!ref.current) return;\n"
            "    const ctx = gsap.context(() => animation(ref.current), ref);\n"
            "    return () => ctx.revert();\n"
            "  }, deps);\n"
            "  return ref;\n"
            "}\n"
        )

    def _gsap_scroll_trigger(self) -> str:
        return (
            "import { useRef, useEffect } from 'react';\n"
            "import gsap from 'gsap';\n"
            "import { ScrollTrigger } from 'gsap/ScrollTrigger';\n\n"
            "gsap.registerPlugin(ScrollTrigger);\n\n"
            "export function useScrollTrigger(animation, options = {}) {\n"
            "  const ref = useRef(null);\n"
            "  useEffect(() => {\n"
            "    if (!ref.current) return;\n"
            "    const trigger = ScrollTrigger.create({\n"
            "      trigger: ref.current,\n"
            "      start: options.start || 'top 80%',\n"
            "      end: options.end || 'bottom 20%',\n"
            "      onEnter: () => animation(ref.current),\n"
            "      once: options.once ?? true,\n"
            "    });\n"
            "    return () => trigger.kill();\n"
            "  }, []);\n"
            "  return ref;\n"
            "}\n"
        )

    def _gsap_screen(self, name: str, components: List[Dict[str, Any]],
                     timeline: AnimationTimeline) -> str:
        lines = [
            "import React, { useRef, useEffect } from 'react';",
            "import gsap from 'gsap';",
            "import { useGSAP } from '../hooks/useGSAP';",
            "",
            f"export default function {name}() {{",
            "  const containerRef = useRef(null);",
            "",
            "  useEffect(() => {",
            "    if (!containerRef.current) return;",
            "    const ctx = gsap.context(() => {",
            "      gsap.from('.animated-item', {",
            "        y: 40, opacity: 0, duration: 0.6,",
            "        stagger: 0.1, ease: 'power2.out',",
            "      });",
            "    }, containerRef);",
            "    return () => ctx.revert();",
            "  }, []);",
            "",
            "  return (",
            f"    <div ref={{containerRef}} style={{{{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}}}>",
            f"      <h1>{name}</h1>",
        ]

        for comp in components:
            label = comp.get("label", comp.get("text", ""))
            comp_type = comp.get("type", "div")
            if comp_type == "Button":
                lines.append(f'      <button className="animated-item" style={{{{ padding: "12px 24px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}}}>{label}</button>')
            else:
                lines.append(f'      <div className="animated-item">{label}</div>')

        lines.extend([
            "    </div>",
            "  );",
            "}",
        ])
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # CSS animations (fallback)
    # ------------------------------------------------------------------

    def _generate_css_animations(self, timeline: AnimationTimeline,
                                  components: List[Dict[str, Any]],
                                  screens: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
        files: Dict[str, str] = {}
        files["src/animations/keyframes.css"] = self._css_keyframes(timeline)
        files["src/animations/animations.css"] = self._css_animation_classes()
        return files

    def _css_keyframes(self, timeline: AnimationTimeline) -> str:
        lines = ["/* EoStudio Generated CSS Keyframes */\n"]

        for clip in timeline.clips:
            name = clip.target_id.replace(".", "-")
            lines.append(f"@keyframes {name} {{")
            for track in clip.tracks:
                for kf in track.keyframes:
                    pct = (kf.time / clip.duration * 100) if clip.duration > 0 else 0
                    prop = self._to_css_prop(track.property_name)
                    val = kf.value
                    if prop == "transform":
                        val = f"translate({val}px)" if isinstance(val, (int, float)) else str(val)
                    lines.append(f"  {pct:.0f}% {{ {prop}: {val}; }}")
            lines.append("}\n")

        return "\n".join(lines)

    def _css_animation_classes(self) -> str:
        return (
            "/* EoStudio Animation Utility Classes */\n\n"
            ".animate-fadeIn { animation: fadeIn 0.5s ease-out forwards; }\n"
            ".animate-fadeInUp { animation: fadeInUp 0.6s ease-out forwards; }\n"
            ".animate-slideUp { animation: slideUp 0.5s cubic-bezier(0.33, 1, 0.68, 1) forwards; }\n"
            ".animate-scaleIn { animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }\n"
            ".animate-bounce { animation: bounce 0.8s ease-out; }\n"
            ".animate-pulse { animation: pulse 2s ease-in-out infinite; }\n"
            ".animate-shake { animation: shake 0.6s linear; }\n\n"
            "@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }\n"
            "@keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }\n"
            "@keyframes slideUp { from { transform: translateY(100px); } to { transform: translateY(0); } }\n"
            "@keyframes scaleIn { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }\n"
            "@keyframes bounce { 0%, 100% { transform: translateY(0); } 25% { transform: translateY(-20px); } 50% { transform: translateY(0); } 75% { transform: translateY(-8px); } }\n"
            "@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }\n"
            "@keyframes shake { 0% { transform: translateX(0); } 10% { transform: translateX(-10px); } 20% { transform: translateX(10px); } 30% { transform: translateX(-10px); } 40% { transform: translateX(10px); } 50% { transform: translateX(-5px); } 100% { transform: translateX(0); } }\n"
        )

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def _package_json(self, library: str) -> str:
        deps: Dict[str, str] = {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.20.0",
        }
        if library == "framer-motion":
            deps["framer-motion"] = "^11.0.0"
        elif library == "gsap":
            deps["gsap"] = "^3.12.0"

        import json
        return json.dumps({
            "name": "eostudio-generated-app",
            "version": "1.0.0",
            "private": True,
            "dependencies": deps,
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
            },
        }, indent=2)

    def _to_motion_prop(self, prop: str) -> str:
        mapping = {"x": "x", "y": "y", "scale": "scale", "rotation": "rotate",
                   "opacity": "opacity", "width": "width", "height": "height"}
        return mapping.get(prop, prop)

    def _to_gsap_prop(self, prop: str) -> str:
        mapping = {"x": "x", "y": "y", "scale": "scale", "rotation": "rotation",
                   "opacity": "opacity", "width": "width", "height": "height"}
        return mapping.get(prop, prop)

    def _to_css_prop(self, prop: str) -> str:
        mapping = {"x": "transform", "y": "transform", "scale": "transform",
                   "rotation": "transform", "opacity": "opacity"}
        return mapping.get(prop, prop)

    def _js_value(self, val: Any) -> str:
        if isinstance(val, dict):
            items = ", ".join(f"{k}: {self._js_value(v)}" for k, v in val.items())
            return f"{{ {items} }}"
        if isinstance(val, list):
            items = ", ".join(self._js_value(v) for v in val)
            return f"[{items}]"
        if isinstance(val, str):
            return f"'{val}'"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        return str(val)

    @staticmethod
    def _component_name(name: str) -> str:
        return "".join(w.capitalize() for w in name.replace("-", " ").replace("_", " ").split())

    @staticmethod
    def _kebab(name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")
