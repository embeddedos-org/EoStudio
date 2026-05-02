"""Git integration for EoStudio IDE.

Provides a comprehensive interface to git operations via subprocess,
suitable for embedding in the EoStudio IDE environment.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Dict, List, Optional


class GitError(Exception):
    """Exception raised when a git operation fails."""

    def __init__(self, message: str, returncode: int = 1, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(message)


class GitIntegration:
    """Full-featured git integration for EoStudio.

    All git operations are executed via the ``git`` binary using
    :func:`subprocess.run`.  The helper :meth:`_run_git` centralises
    argument construction, working-directory handling and error
    propagation.

    Parameters
    ----------
    workspace_path:
        Root directory of the git repository.  Defaults to the current
        working directory.
    """

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = os.path.abspath(workspace_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command and return the completed process.

        Parameters
        ----------
        *args:
            Arguments passed directly to ``git``.
        check:
            If *True* (the default), raise :class:`GitError` when the
            command exits with a non-zero status.

        Returns
        -------
        subprocess.CompletedProcess
        """
        cmd = ["git", *args]
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            raise GitError("git executable not found - is git installed?")
        except subprocess.TimeoutExpired:
            raise GitError(f"git command timed out: {' '.join(cmd)}")

        if check and result.returncode != 0:
            stderr = result.stderr.strip()
            raise GitError(
                f"git {args[0]} failed (exit {result.returncode}): {stderr}",
                returncode=result.returncode,
                stderr=stderr,
            )
        return result

    # ------------------------------------------------------------------
    # Repository state
    # ------------------------------------------------------------------

    def is_repo(self) -> bool:
        """Return *True* if the workspace is inside a git repository."""
        try:
            result = self._run_git("rev-parse", "--is-inside-work-tree", check=False)
            return result.returncode == 0 and result.stdout.strip() == "true"
        except GitError:
            return False

    def init(self) -> bool:
        """Initialise a new git repository in the workspace directory."""
        self._run_git("init")
        return True

    def clone(self, url: str, directory: str | None = None) -> bool:
        """Clone a remote repository.

        Parameters
        ----------
        url:
            URL of the remote repository to clone.
        directory:
            Optional local directory name.  When *None* git will choose
            the default.
        """
        cmd: list[str] = ["clone", url]
        if directory is not None:
            cmd.append(directory)
        self._run_git(*cmd)
        return True

    # ------------------------------------------------------------------
    # Status / diff
    # ------------------------------------------------------------------

    def status(self) -> List[Dict[str, str]]:
        """Return the working-tree status as a list of dicts.

        Each dict has the keys ``"status"`` (the two-character porcelain
        code, e.g. ``" M"``, ``"??"``) and ``"file"`` (the path relative
        to the repository root).
        """
        result = self._run_git("status", "--porcelain")
        entries: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            # Porcelain v1: first two chars are the status code, then a
            # space, then the filename.  Renames use " -> " notation.
            status_code = line[:2]
            file_path = line[3:]
            entries.append({"status": status_code, "file": file_path})
        return entries

    def diff(self, staged: bool = False, file: str | None = None) -> str:
        """Return the diff output as a string.

        Parameters
        ----------
        staged:
            If *True*, show the staged (cached) diff instead of the
            working-tree diff.
        file:
            Optionally restrict the diff to a single file.
        """
        cmd: list[str] = ["diff"]
        if staged:
            cmd.append("--cached")
        if file is not None:
            cmd.extend(["--", file])
        result = self._run_git(*cmd)
        return result.stdout

    # ------------------------------------------------------------------
    # Staging
    # ------------------------------------------------------------------

    def add(self, files: List[str] | None = None) -> bool:
        """Stage files for the next commit.

        Parameters
        ----------
        files:
            List of file paths to add.  When *None*, all changes are
            staged (``git add -A``).
        """
        if files is None:
            self._run_git("add", "-A")
        else:
            self._run_git("add", "--", *files)
        return True

    def reset(self, files: List[str] | None = None, hard: bool = False) -> bool:
        """Reset the index or working tree.

        Parameters
        ----------
        files:
            List of file paths to unstage.  When *None* the entire
            index is reset.
        hard:
            Perform a hard reset (discard working-tree changes).
        """
        cmd: list[str] = ["reset"]
        if hard:
            cmd.append("--hard")
        if files is not None:
            cmd.extend(["--", *files])
        self._run_git(*cmd)
        return True

    # ------------------------------------------------------------------
    # Committing
    # ------------------------------------------------------------------

    def commit(self, message: str, amend: bool = False) -> bool:
        """Create a commit with the given message.

        Parameters
        ----------
        message:
            The commit message.
        amend:
            If *True*, amend the previous commit instead of creating a
            new one.
        """
        cmd: list[str] = ["commit", "-m", message]
        if amend:
            cmd.append("--amend")
        self._run_git(*cmd)
        return True

    # ------------------------------------------------------------------
    # Remote operations
    # ------------------------------------------------------------------

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
    ) -> bool:
        """Push commits to a remote.

        Parameters
        ----------
        remote:
            Remote name.
        branch:
            Branch to push.  When *None* git will push the current
            branch (or follow ``push.default``).
        force:
            Use ``--force-with-lease`` for a safer forced push.
        """
        cmd: list[str] = ["push"]
        if force:
            cmd.append("--force-with-lease")
        cmd.append(remote)
        if branch is not None:
            cmd.append(branch)
        self._run_git(*cmd)
        return True

    def pull(
        self,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> bool:
        """Pull changes from a remote.

        Parameters
        ----------
        remote:
            Remote name.
        branch:
            Branch to pull.  When *None* git will pull the current
            tracking branch.
        rebase:
            If *True*, rebase local commits on top of the fetched
            branch instead of merging.
        """
        cmd: list[str] = ["pull"]
        if rebase:
            cmd.append("--rebase")
        cmd.append(remote)
        if branch is not None:
            cmd.append(branch)
        self._run_git(*cmd)
        return True

    def fetch(self, remote: str = "origin", prune: bool = False) -> bool:
        """Fetch objects and refs from a remote.

        Parameters
        ----------
        remote:
            Remote name.
        prune:
            If *True*, remove any remote-tracking references that no
            longer exist on the remote.
        """
        cmd: list[str] = ["fetch", remote]
        if prune:
            cmd.append("--prune")
        self._run_git(*cmd)
        return True

    def remote_url(self, remote: str = "origin") -> str:
        """Return the URL configured for *remote*."""
        result = self._run_git("remote", "get-url", remote)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Branching
    # ------------------------------------------------------------------

    def branch(self) -> str:
        """Return the name of the current branch.

        Returns ``"HEAD"`` when in detached HEAD state.
        """
        result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()

    def branches(self, all: bool = False) -> List[str]:
        """List branch names.

        Parameters
        ----------
        all:
            If *True*, include remote-tracking branches as well.
        """
        cmd: list[str] = ["branch", "--list", "--no-color"]
        if all:
            cmd.append("--all")
        result = self._run_git(*cmd)
        out: list[str] = []
        for line in result.stdout.splitlines():
            name = line.lstrip("* ").strip()
            if name:
                out.append(name)
        return out

    def checkout(self, branch: str, create: bool = False) -> bool:
        """Switch branches or create and switch.

        Parameters
        ----------
        branch:
            Target branch name.
        create:
            If *True*, create the branch before switching (``-b``).
        """
        cmd: list[str] = ["checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)
        self._run_git(*cmd)
        return True

    # ------------------------------------------------------------------
    # Merging / rebasing
    # ------------------------------------------------------------------

    def merge(self, branch: str, no_ff: bool = False) -> bool:
        """Merge *branch* into the current branch.

        Parameters
        ----------
        branch:
            Branch (or ref) to merge.
        no_ff:
            If *True*, always create a merge commit even when
            fast-forward is possible.
        """
        cmd: list[str] = ["merge"]
        if no_ff:
            cmd.append("--no-ff")
        cmd.append(branch)
        self._run_git(*cmd)
        return True

    def rebase(self, branch: str, interactive: bool = False) -> bool:
        """Rebase the current branch onto *branch*.

        Parameters
        ----------
        branch:
            Upstream branch to rebase onto.
        interactive:
            If *True*, start an interactive rebase.  Note: this will
            open an editor unless ``GIT_SEQUENCE_EDITOR`` is set.
        """
        cmd: list[str] = ["rebase"]
        if interactive:
            cmd.append("--interactive")
        cmd.append(branch)
        self._run_git(*cmd)
        return True

    # ------------------------------------------------------------------
    # Stash
    # ------------------------------------------------------------------

    def stash(self, message: str | None = None) -> bool:
        """Stash the current working-tree changes.

        Parameters
        ----------
        message:
            Optional message to describe the stash entry.
        """
        cmd: list[str] = ["stash", "push"]
        if message is not None:
            cmd.extend(["-m", message])
        self._run_git(*cmd)
        return True

    def stash_pop(self) -> bool:
        """Pop the most recent stash entry."""
        self._run_git("stash", "pop")
        return True

    def stash_list(self) -> List[str]:
        """Return a list of stash entries (human-readable descriptions)."""
        result = self._run_git("stash", "list")
        return [line for line in result.stdout.splitlines() if line]

    # ------------------------------------------------------------------
    # Log / blame
    # ------------------------------------------------------------------

    def log(self, n: int = 10, oneline: bool = True) -> List[Dict[str, str]]:
        """Return recent commits.

        Parameters
        ----------
        n:
            Maximum number of commits to return.
        oneline:
            If *True*, return a compact format with ``hash`` and
            ``message`` keys.  If *False*, also include ``author`` and
            ``date``.

        Returns
        -------
        list[dict[str, str]]
            Each dict contains at least ``"hash"`` and ``"message"``.
            When *oneline* is *False*, ``"author"`` and ``"date"`` are
            also present.
        """
        if oneline:
            result = self._run_git(
                "log",
                f"-{n}",
                "--pretty=format:%h %s",
            )
            entries: list[dict[str, str]] = []
            for line in result.stdout.splitlines():
                if not line:
                    continue
                parts = line.split(" ", 1)
                entries.append({
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else "",
                })
            return entries

        # Detailed format: use a separator that is unlikely to appear in
        # commit messages so we can split reliably.
        sep = "---GIT_FIELD_SEP---"
        fmt = sep.join(["%h", "%an", "%ai", "%s"])
        result = self._run_git(
            "log",
            f"-{n}",
            f"--pretty=format:{fmt}",
        )
        entries = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            parts = line.split(sep, 3)
            if len(parts) < 4:
                continue
            entries.append({
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3],
            })
        return entries

    def blame(self, file: str) -> List[Dict[str, str]]:
        """Return line-by-line blame information for *file*.

        Each entry contains:

        * ``commit`` -- abbreviated commit hash
        * ``author`` -- author name
        * ``date`` -- author date (ISO-ish)
        * ``line_no`` -- 1-based line number
        * ``content`` -- line content
        """
        result = self._run_git("blame", "--porcelain", "--", file)
        entries: list[dict[str, str]] = []
        current: dict[str, str] = {}
        # Porcelain blame output: header line starts with a 40-char hex
        # hash, followed by orig-line final-line [group-count].
        # Then key-value pairs, then a TAB-prefixed content line.
        header_re = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)")
        for line in result.stdout.splitlines():
            header_match = header_re.match(line)
            if header_match:
                current = {
                    "commit": header_match.group(1)[:8],
                    "line_no": header_match.group(3),
                }
            elif line.startswith("author "):
                current["author"] = line[len("author "):]
            elif line.startswith("author-time "):
                current.setdefault("date", line[len("author-time "):])
            elif line.startswith("\t"):
                current["content"] = line[1:]
                entries.append(current)
                current = {}
        return entries

    # ------------------------------------------------------------------
    # Conflict helpers
    # ------------------------------------------------------------------

    def has_conflicts(self) -> bool:
        """Return *True* if the working tree contains merge conflicts."""
        return len(self.get_conflicts()) > 0

    def get_conflicts(self) -> List[str]:
        """Return a list of files with unresolved merge conflicts.

        Uses ``git diff --name-only --diff-filter=U`` which lists
        unmerged paths.
        """
        result = self._run_git(
            "diff", "--name-only", "--diff-filter=U", check=False,
        )
        if result.returncode != 0:
            return []
        return [f for f in result.stdout.splitlines() if f.strip()]
