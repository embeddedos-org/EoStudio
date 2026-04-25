"""Production UI Kit Generator — generates polished, accessible React components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComponentDef:
    """Definition of a UI component with variants, props, and accessibility."""
    name: str
    category: str  # layout, input, display, feedback, navigation, overlay
    description: str = ""
    props: List[Dict[str, str]] = field(default_factory=list)
    variants: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    has_dark_mode: bool = True
    aria_attributes: List[str] = field(default_factory=list)
    keyboard_support: List[str] = field(default_factory=list)


# 30+ production components
COMPONENT_LIBRARY: Dict[str, ComponentDef] = {
    "Button": ComponentDef("Button", "input", "Clickable button with variants",
                           variants=["primary", "secondary", "ghost", "danger", "outline"],
                           sizes=["sm", "md", "lg"],
                           aria_attributes=["aria-label", "aria-disabled"],
                           keyboard_support=["Enter", "Space"]),
    "Input": ComponentDef("Input", "input", "Text input with validation",
                          variants=["outlined", "filled", "underline"],
                          sizes=["sm", "md", "lg"],
                          aria_attributes=["aria-label", "aria-invalid", "aria-describedby"]),
    "Textarea": ComponentDef("Textarea", "input", "Multi-line text input",
                             variants=["outlined", "filled"], sizes=["sm", "md", "lg"]),
    "Select": ComponentDef("Select", "input", "Dropdown select",
                           variants=["outlined", "filled"],
                           keyboard_support=["ArrowUp", "ArrowDown", "Enter", "Escape"]),
    "Checkbox": ComponentDef("Checkbox", "input", "Checkbox with label",
                             aria_attributes=["aria-checked"],
                             keyboard_support=["Space"]),
    "Radio": ComponentDef("Radio", "input", "Radio button group",
                          keyboard_support=["ArrowUp", "ArrowDown"]),
    "Toggle": ComponentDef("Toggle", "input", "Toggle switch",
                           sizes=["sm", "md", "lg"],
                           aria_attributes=["aria-checked", "role=switch"]),
    "Slider": ComponentDef("Slider", "input", "Range slider",
                           aria_attributes=["aria-valuemin", "aria-valuemax", "aria-valuenow"]),
    "Card": ComponentDef("Card", "display", "Content card with header/body/footer",
                         variants=["elevated", "outlined", "filled"]),
    "Avatar": ComponentDef("Avatar", "display", "User avatar with fallback",
                           sizes=["xs", "sm", "md", "lg", "xl"],
                           variants=["circular", "rounded", "square"]),
    "Badge": ComponentDef("Badge", "display", "Status badge/tag",
                          variants=["solid", "outline", "subtle"],
                          sizes=["sm", "md"]),
    "Alert": ComponentDef("Alert", "feedback", "Alert message",
                          variants=["info", "success", "warning", "error"],
                          aria_attributes=["role=alert"]),
    "Toast": ComponentDef("Toast", "feedback", "Toast notification",
                          variants=["info", "success", "warning", "error"],
                          aria_attributes=["role=status", "aria-live=polite"]),
    "Dialog": ComponentDef("Dialog", "overlay", "Modal dialog",
                           aria_attributes=["role=dialog", "aria-modal=true", "aria-labelledby"],
                           keyboard_support=["Escape", "Tab trap"]),
    "Sheet": ComponentDef("Sheet", "overlay", "Bottom/side sheet",
                          variants=["bottom", "left", "right"]),
    "Dropdown": ComponentDef("Dropdown", "overlay", "Dropdown menu",
                             keyboard_support=["ArrowUp", "ArrowDown", "Enter", "Escape"]),
    "Tooltip": ComponentDef("Tooltip", "overlay", "Tooltip on hover",
                            aria_attributes=["role=tooltip"]),
    "Tabs": ComponentDef("Tabs", "navigation", "Tab navigation",
                         variants=["underline", "pills", "enclosed"],
                         keyboard_support=["ArrowLeft", "ArrowRight"]),
    "Breadcrumb": ComponentDef("Breadcrumb", "navigation", "Breadcrumb navigation",
                               aria_attributes=["aria-label=Breadcrumb"]),
    "Pagination": ComponentDef("Pagination", "navigation", "Page pagination"),
    "Sidebar": ComponentDef("Sidebar", "navigation", "Collapsible sidebar"),
    "Navbar": ComponentDef("Navbar", "navigation", "Top navigation bar"),
    "Table": ComponentDef("Table", "display", "Data table with sorting",
                          aria_attributes=["role=table"]),
    "Skeleton": ComponentDef("Skeleton", "feedback", "Loading skeleton",
                             variants=["text", "circular", "rectangular"]),
    "Progress": ComponentDef("Progress", "feedback", "Progress bar",
                             variants=["linear", "circular"],
                             aria_attributes=["role=progressbar", "aria-valuenow"]),
    "Spinner": ComponentDef("Spinner", "feedback", "Loading spinner",
                            sizes=["sm", "md", "lg"]),
    "Divider": ComponentDef("Divider", "layout", "Horizontal/vertical divider"),
    "Stack": ComponentDef("Stack", "layout", "Flex stack layout",
                          variants=["horizontal", "vertical"]),
    "Grid": ComponentDef("Grid", "layout", "CSS grid layout"),
    "Container": ComponentDef("Container", "layout", "Max-width container"),
    "AspectRatio": ComponentDef("AspectRatio", "layout", "Aspect ratio container"),
    "ScrollArea": ComponentDef("ScrollArea", "layout", "Custom scrollbar area"),
    "Accordion": ComponentDef("Accordion", "display", "Collapsible accordion",
                              keyboard_support=["Enter", "Space", "ArrowUp", "ArrowDown"]),
    "CommandPalette": ComponentDef("CommandPalette", "overlay", "Cmd+K command palette",
                                   keyboard_support=["Cmd+K", "ArrowUp", "ArrowDown", "Enter"]),
    # Compound components
    "Form": ComponentDef("Form", "input", "Form with validation, field groups, and submit handling",
                         variants=["vertical", "horizontal", "inline"],
                         aria_attributes=["role=form", "aria-label"],
                         keyboard_support=["Tab", "Enter"]),
    "DataTable": ComponentDef("DataTable", "display", "Data table with sorting, filtering, and pagination",
                              variants=["simple", "striped", "bordered"],
                              sizes=["sm", "md", "lg"],
                              aria_attributes=["role=table", "aria-sort", "aria-label"]),
    "FileUpload": ComponentDef("FileUpload", "input", "File upload with drag-and-drop and preview",
                               variants=["dropzone", "button", "inline"],
                               aria_attributes=["aria-label", "role=button"]),
    "DatePicker": ComponentDef("DatePicker", "input", "Date picker with calendar popup",
                               sizes=["sm", "md", "lg"],
                               aria_attributes=["aria-label", "role=dialog"],
                               keyboard_support=["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape"]),
    "ColorPicker": ComponentDef("ColorPicker", "input", "Color picker with presets and custom input",
                                sizes=["sm", "md", "lg"],
                                aria_attributes=["aria-label"]),
}


class UIKitGenerator:
    """Generates production-quality React components with TypeScript + Tailwind.

    Supports per-project customization, responsive variants, animation variants,
    and Storybook story generation.
    """

    def __init__(self, style: str = "shadcn") -> None:
        self.style = style
        self._design_tokens: Dict[str, Any] = {}

    def customize_for_project(self, spec_data: Dict[str, Any]) -> None:
        """Configure component generation based on project spec (colors, spacing, typography)."""
        design = spec_data.get("design_spec", {})
        tech = spec_data.get("tech_spec", {})

        # Extract design tokens from spec variables or defaults
        variables = design.get("variables", {})
        self._design_tokens = {
            "primary_color": variables.get("primary_color", "#2563eb"),
            "secondary_color": variables.get("secondary_color", "#f1f5f9"),
            "accent_color": variables.get("accent_color", "#8b5cf6"),
            "font_family": variables.get("font_family", "Inter, system-ui, sans-serif"),
            "border_radius": variables.get("border_radius", "0.5rem"),
            "spacing_unit": variables.get("spacing_unit", "0.25rem"),
        }

    def generate_all(self, include_stories: bool = False,
                     include_responsive: bool = True,
                     include_animations: bool = True) -> Dict[str, str]:
        """Generate all components with optional stories, responsive, and animation variants."""
        files: Dict[str, str] = {}
        files["src/components/ui/index.ts"] = self._generate_index()
        files["src/lib/utils.ts"] = self._generate_utils()
        files["tailwind.config.js"] = self._generate_tailwind_config()

        if include_animations:
            files["src/lib/animations.ts"] = self._generate_animation_utils()

        for name, comp in COMPONENT_LIBRARY.items():
            filename = f"src/components/ui/{self._kebab(name)}.tsx"
            files[filename] = self._generate_component(
                comp,
                responsive=include_responsive,
                animated=include_animations,
            )

            if include_stories:
                story_filename = f"src/components/ui/{self._kebab(name)}.stories.tsx"
                files[story_filename] = self._generate_story(comp)

        return files

    def generate_component(self, name: str) -> Optional[str]:
        """Generate a single component by name."""
        comp = COMPONENT_LIBRARY.get(name)
        if comp:
            return self._generate_component(comp)
        return None

    def _generate_component(self, comp: ComponentDef,
                            responsive: bool = False,
                            animated: bool = False) -> str:
        """Generate a single React component with TypeScript, responsive, and animation support."""
        name = comp.name
        kebab = self._kebab(name)
        variants_type = " | ".join(f'"{v}"' for v in comp.variants) if comp.variants else '"default"'
        sizes_type = " | ".join(f'"{s}"' for s in comp.sizes) if comp.sizes else '"md"'

        lines = [
            f'import React from "react";',
            f'import {{ cn }} from "@/lib/utils";',
        ]
        if animated:
            lines.append(f'import {{ motion }} from "framer-motion";')
            lines.append(f'import {{ fadeIn }} from "@/lib/animations";')
        lines.append("")

        lines.append(f"export interface {name}Props extends React.HTMLAttributes<HTMLElement> {{")
        if comp.variants:
            lines.append(f"  variant?: {variants_type};")
        if comp.sizes:
            lines.append(f"  size?: {sizes_type};")
        if responsive:
            lines.append(f'  responsive?: boolean;')
        if animated:
            lines.append(f'  animated?: boolean;')
        lines.extend([
            "  disabled?: boolean;",
            "  children?: React.ReactNode;",
            "}",
            "",
        ])

        # Variant styles map
        if comp.variants:
            lines.append(f"const variants: Record<string, string> = {{")
            variant_styles = {
                "primary": "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
                "secondary": "bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500",
                "ghost": "bg-transparent hover:bg-gray-100 text-gray-700",
                "danger": "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
                "outline": "border border-gray-300 bg-transparent hover:bg-gray-50",
                "outlined": "border border-gray-300 bg-white",
                "filled": "bg-gray-100 border-transparent",
                "info": "bg-blue-50 text-blue-800 border-blue-200",
                "success": "bg-green-50 text-green-800 border-green-200",
                "warning": "bg-yellow-50 text-yellow-800 border-yellow-200",
                "error": "bg-red-50 text-red-800 border-red-200",
                "elevated": "bg-white shadow-md",
                "subtle": "bg-opacity-10",
                "solid": "text-white",
                "underline": "border-b-2 border-blue-600",
                "pills": "rounded-full bg-blue-100",
                "enclosed": "border rounded-t-md",
            }
            for v in comp.variants:
                style = variant_styles.get(v, "bg-gray-100")
                lines.append(f'  {v}: "{style}",')
            lines.append("};")
            lines.append("")

        if comp.sizes:
            lines.append("const sizes: Record<string, string> = {")
            size_styles = {"xs": "text-xs px-2 py-0.5", "sm": "text-sm px-3 py-1.5",
                           "md": "text-base px-4 py-2", "lg": "text-lg px-6 py-3",
                           "xl": "text-xl px-8 py-4"}
            for s in comp.sizes:
                lines.append(f'  {s}: "{size_styles.get(s, "px-4 py-2")}",')
            lines.append("};")
            lines.append("")

        # Responsive breakpoint classes
        if responsive and comp.sizes:
            lines.append("const responsiveClasses = \"sm:px-3 sm:py-1.5 sm:text-sm md:px-4 md:py-2 md:text-base lg:px-6 lg:py-3 lg:text-lg\";")
            lines.append("")

        # Component function
        prop_destructure = ""
        if comp.variants:
            prop_destructure += f'variant = "{comp.variants[0]}", '
        if comp.sizes:
            prop_destructure += f'size = "{comp.sizes[0]}", '
        if responsive:
            prop_destructure += "responsive: isResponsive, "
        if animated:
            prop_destructure += "animated = true, "
        prop_destructure += "disabled, className, children, ...props"

        lines.extend([
            f"export const {name} = React.forwardRef<HTMLElement, {name}Props>((",
            f"  {{ {prop_destructure} }},",
            "  ref",
            ") => {",
        ])

        # Use motion component if animated
        if animated:
            lines.extend([
                f"  const Comp = animated ? motion.div : \"div\";",
                f"  const animationProps = animated ? fadeIn : {{}};",
            ])

        lines.append("  return (")

        # Element based on category
        tag = {"input": "input" if name in ("Input", "Textarea") else "button",
               "display": "div", "feedback": "div", "overlay": "div",
               "navigation": "nav", "layout": "div"}.get(comp.category, "div")

        aria_attrs = ""
        for attr in comp.aria_attributes:
            if "=" in attr:
                k, v = attr.split("=", 1)
                aria_attrs += f' {k}="{v}"'
            else:
                aria_attrs += f" {attr}"

        base_class = {
            "Button": "inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none",
            "Input": "w-full rounded-md border px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50",
            "Card": "rounded-lg border bg-white p-6",
            "Badge": "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
            "Alert": "relative w-full rounded-lg border p-4",
        }.get(name, "")

        variant_ref = f"variants[variant]" if comp.variants else '""'
        size_ref = f"sizes[size]" if comp.sizes else '""'

        responsive_ref = "isResponsive ? responsiveClasses : \"\"" if responsive and comp.sizes else '""'

        lines.extend([
            f'    <{tag}',
            f'      ref={{ref as any}}',
            f'      className={{cn("{base_class}", {variant_ref}, {size_ref}, {responsive_ref}, className)}}',
            f"      disabled={{disabled}}",
        ])
        if animated:
            lines.append(f"      {{...animationProps}}")
        lines.extend([
            f"      {{...props}}",
            f"    >",
            f"      {{children}}",
            f"    </{tag}>",
            "  );",
            "});",
            "",
            f'{name}.displayName = "{name}";',
            "",
            f"export default {name};",
        ])

        return "\n".join(lines) + "\n"

    def _generate_index(self) -> str:
        lines = [f'export {{ {name} }} from "./{self._kebab(name)}";'
                 for name in COMPONENT_LIBRARY]
        return "\n".join(lines) + "\n"

    def _generate_utils(self) -> str:
        return (
            'import { type ClassValue, clsx } from "clsx";\n'
            'import { twMerge } from "tailwind-merge";\n\n'
            "export function cn(...inputs: ClassValue[]) {\n"
            "  return twMerge(clsx(inputs));\n"
            "}\n"
        )

    def _generate_tailwind_config(self) -> str:
        primary = self._design_tokens.get("primary_color", "#2563eb")
        secondary = self._design_tokens.get("secondary_color", "#f1f5f9")
        accent = self._design_tokens.get("accent_color", "#8b5cf6")
        radius = self._design_tokens.get("border_radius", "0.5rem")
        font = self._design_tokens.get("font_family", "Inter, system-ui, sans-serif")

        return (
            '/** @type {import("tailwindcss").Config} */\n'
            "module.exports = {\n"
            "  darkMode: ['class'],\n"
            '  content: ["./src/**/*.{ts,tsx}"],\n'
            "  theme: {\n"
            "    extend: {\n"
            f'      fontFamily: {{ sans: ["{font}"] }},\n'
            "      colors: {\n"
            f'        primary: {{ DEFAULT: "{primary}", foreground: "#ffffff" }},\n'
            f'        secondary: {{ DEFAULT: "{secondary}", foreground: "#1e293b" }},\n'
            f'        accent: {{ DEFAULT: "{accent}", foreground: "#ffffff" }},\n'
            '        destructive: { DEFAULT: "#dc2626", foreground: "#ffffff" },\n'
            '        muted: { DEFAULT: "#f1f5f9", foreground: "#64748b" },\n'
            '        border: "#e2e8f0",\n'
            '        ring: "#2563eb",\n'
            "      },\n"
            f'      borderRadius: {{ lg: "{radius}", md: "0.375rem", sm: "0.25rem" }},\n'
            "    },\n"
            "  },\n"
            "  plugins: [],\n"
            "};\n"
        )

    def _generate_animation_utils(self) -> str:
        """Generate Framer Motion animation presets."""
        return (
            'import type { Variants } from "framer-motion";\n\n'
            "export const fadeIn = {\n"
            '  initial: { opacity: 0, y: 8 },\n'
            '  animate: { opacity: 1, y: 0 },\n'
            '  transition: { duration: 0.2, ease: "easeOut" },\n'
            "};\n\n"
            "export const fadeOut = {\n"
            '  exit: { opacity: 0, y: -8 },\n'
            '  transition: { duration: 0.15, ease: "easeIn" },\n'
            "};\n\n"
            "export const slideIn: Variants = {\n"
            '  hidden: { x: -20, opacity: 0 },\n'
            '  visible: { x: 0, opacity: 1, transition: { duration: 0.3 } },\n'
            "};\n\n"
            "export const scaleIn: Variants = {\n"
            '  hidden: { scale: 0.95, opacity: 0 },\n'
            '  visible: { scale: 1, opacity: 1, transition: { duration: 0.2 } },\n'
            "};\n\n"
            "export const staggerChildren: Variants = {\n"
            "  visible: {\n"
            "    transition: { staggerChildren: 0.05 },\n"
            "  },\n"
            "};\n"
        )

    def _generate_story(self, comp: ComponentDef) -> str:
        """Generate a Storybook story for a component."""
        name = comp.name
        kebab = self._kebab(name)
        lines = [
            f'import type {{ Meta, StoryObj }} from "@storybook/react";',
            f'import {{ {name} }} from "./{kebab}";',
            "",
            f"const meta: Meta<typeof {name}> = {{",
            f'  title: "UI/{name}",',
            f"  component: {name},",
            f"  tags: [\"autodocs\"],",
        ]

        # Add argTypes for variants
        if comp.variants:
            lines.append("  argTypes: {")
            lines.append("    variant: {")
            lines.append(f'      control: "select",')
            lines.append(f"      options: {comp.variants},")
            lines.append("    },")
            if comp.sizes:
                lines.append("    size: {")
                lines.append(f'      control: "select",')
                lines.append(f"      options: {comp.sizes},")
                lines.append("    },")
            lines.append("  },")

        lines.extend([
            "};",
            "",
            "export default meta;",
            f"type Story = StoryObj<typeof {name}>;",
            "",
            f'export const Default: Story = {{',
            f"  args: {{",
            f'    children: "{name}",',
        ])
        if comp.variants:
            lines.append(f'    variant: "{comp.variants[0]}",')
        if comp.sizes:
            lines.append(f'    size: "md",')
        lines.extend([
            "  },",
            "};",
        ])

        # Add variant stories
        for v in comp.variants[:3]:
            story_name = v.title().replace("_", "")
            lines.extend([
                "",
                f"export const {story_name}: Story = {{",
                f"  args: {{",
                f'    children: "{name} ({v})",',
                f'    variant: "{v}",',
                "  },",
                "};",
            ])

        return "\n".join(lines) + "\n"

    @staticmethod
    def _kebab(name: str) -> str:
        import re
        return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
