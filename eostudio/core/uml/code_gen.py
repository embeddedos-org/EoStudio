"""UML code generation — generate source code from UML class diagrams."""

from __future__ import annotations

from typing import List

from eostudio.core.uml.diagrams import UMLClass, UMLDiagram


class UMLCodeGen:
    @staticmethod
    def generate_python(diagram: UMLDiagram) -> str:
        lines: List[str] = [f'"""Auto-generated from UML diagram: {diagram.name}"""', ""]
        for cls in diagram.classes:
            lines.append(f"class {cls.name}:")
            if not cls.attributes and not cls.methods:
                lines.append("    pass")
            for attr in cls.attributes:
                lines.append(f"    {attr} = None")
            if cls.attributes and cls.methods:
                lines.append("")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"    def {name}(self):")
                lines.append(f"        raise NotImplementedError")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_java(diagram: UMLDiagram) -> str:
        lines: List[str] = [f"// Auto-generated from UML diagram: {diagram.name}", ""]
        for cls in diagram.classes:
            lines.append(f"public class {cls.name} {{")
            for attr in cls.attributes:
                lines.append(f"    private Object {attr};")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"    public void {name}() {{ }}")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_kotlin(diagram: UMLDiagram) -> str:
        lines: List[str] = [f"// Auto-generated from UML diagram: {diagram.name}", ""]
        for cls in diagram.classes:
            lines.append(f"class {cls.name} {{")
            for attr in cls.attributes:
                lines.append(f"    var {attr}: Any? = null")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"    fun {name}() {{ TODO() }}")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_typescript(diagram: UMLDiagram) -> str:
        lines: List[str] = [f"// Auto-generated from UML diagram: {diagram.name}", ""]
        for cls in diagram.classes:
            lines.append(f"export class {cls.name} {{")
            for attr in cls.attributes:
                lines.append(f"  {attr}: any;")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"  {name}(): void {{ }}")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_cpp(diagram: UMLDiagram) -> str:
        lines: List[str] = [f"// Auto-generated from UML diagram: {diagram.name}", "#pragma once", ""]
        for cls in diagram.classes:
            lines.append(f"class {cls.name} {{")
            lines.append("public:")
            for attr in cls.attributes:
                lines.append(f"    int {attr};")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"    void {name}();")
            lines.append("};")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_csharp(diagram: UMLDiagram) -> str:
        lines: List[str] = [f"// Auto-generated from UML diagram: {diagram.name}", ""]
        for cls in diagram.classes:
            lines.append(f"public class {cls.name}")
            lines.append("{")
            for attr in cls.attributes:
                lines.append(f"    public object {attr} {{ get; set; }}")
            for method in cls.methods:
                name = method.split("(")[0].strip()
                lines.append(f"    public void {name}() {{ }}")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)
