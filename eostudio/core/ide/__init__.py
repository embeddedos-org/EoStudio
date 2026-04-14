"""IDE subpackage — syntax highlighting, language server, git, extensions, etc."""

from eostudio.core.ide.syntax import SyntaxHighlighter
from eostudio.core.ide.language_server import LanguageServer
from eostudio.core.ide.git_integration import GitIntegration
from eostudio.core.ide.extensions import ExtensionManager
from eostudio.core.ide.project_manager import ProjectManager
from eostudio.core.ide.terminal import TerminalEmulator
from eostudio.core.ide.debugger import Debugger
from eostudio.core.ide.cloud import CloudSync

__all__ = [
    "SyntaxHighlighter", "LanguageServer", "GitIntegration",
    "ExtensionManager", "ProjectManager", "TerminalEmulator",
    "Debugger", "CloudSync",
]
