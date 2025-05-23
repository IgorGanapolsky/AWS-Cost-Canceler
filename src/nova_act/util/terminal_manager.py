# Copyright 2025 Amazon Inc

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys

DEFAULT_TERMINAL_COLS = 80

if os.name == "nt":
    # Windows-specific keyboard handling
    import msvcrt  # noqa: F401
else:
    import termios


class TerminalInputManager:
    """
    Terminal Manager inspired by: https://simondlevy.academic.wlu.edu/files/software/kbhit.py
    """

    fd: int
    new_term: list
    old_term: list
    is_interactive: bool = False

    def __init__(self):
        # Check if running in an interactive terminal
        self.is_interactive = sys.stdin.isatty() and os.isatty(sys.stdin.fileno())

    def __enter__(self):
        if not self.is_interactive:
            return self

        if os.name == "nt":
            # No equivalent setup required for Windows.
            pass
        else:
            try:
                # Save the terminal settings
                self.fd = sys.stdin.fileno()
                self.new_term = termios.tcgetattr(self.fd)
                self.old_term = termios.tcgetattr(self.fd)

                # New terminal setting unbuffered
                self.new_term[3] = self.new_term[3] & ~termios.ICANON & ~termios.ECHO
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)
            except termios.error:
                # Handle case where terminal manipulation fails
                self.is_interactive = False

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.is_interactive:
            return

        if os.name != "nt":
            try:
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)
            except termios.error:
                pass  # Ignore errors when restoring terminal settings
