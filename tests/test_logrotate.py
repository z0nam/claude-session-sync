"""Tests for bin/claude-remote-logrotate and its hook in bin/claude-remote.

Run: python3 -m unittest discover -s tests
"""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")


def load_rotator():
    path = os.path.join(BIN, "claude-remote-logrotate")
    loader = importlib.machinery.SourceFileLoader("claude_remote_logrotate", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


lr = load_rotator()


def wait_for(cond, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.1)
    return cond()


class CopyTruncateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = os.path.join(self.tmp.name, "out.log")

    def tearDown(self):
        self.tmp.cleanup()

    def write_lines(self, n, width=99):
        with open(self.log, "wb") as f:
            for i in range(n):
                f.write(("%06d " % i).encode() + b"x" * (width - 7) + b"\n")

    def test_small_file_untouched(self):
        self.write_lines(10)
        self.assertFalse(lr.copytruncate(self.log, 10_000))
        self.assertEqual(os.path.getsize(self.log), 1000)
        self.assertFalse(os.path.exists(self.log + ".1"))

    def test_missing_file_is_noop(self):
        self.assertFalse(lr.copytruncate(self.log, 10))

    def test_rotates_tail_in_place(self):
        self.write_lines(1000)  # 100_000 bytes
        ino = os.stat(self.log).st_ino
        self.assertTrue(lr.copytruncate(self.log, 10_000))
        self.assertEqual(os.stat(self.log).st_ino, ino)  # same inode, not renamed
        self.assertEqual(os.path.getsize(self.log), 0)
        with open(self.log + ".1", "rb") as f:
            kept = f.read()
        self.assertLessEqual(len(kept), 10_000)
        self.assertTrue(kept.startswith(b"0009"))  # starts on a line boundary
        self.assertTrue(kept.endswith(b"000999 " + b"x" * 92 + b"\n"))
        self.assertFalse(os.path.exists(self.log + ".1.tmp"))

    def test_keeps_single_generation(self):
        self.write_lines(1000)
        lr.copytruncate(self.log, 10_000)
        self.write_lines(500)
        lr.copytruncate(self.log, 10_000)
        names = sorted(os.listdir(self.tmp.name))
        self.assertEqual(names, ["out.log", "out.log.1"])
        with open(self.log + ".1", "rb") as f:
            self.assertIn(b"000499 ", f.read())

    def test_append_writer_continues_from_zero(self):
        # launchd opens StandardOutPath with O_APPEND; emulate that writer.
        fd = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, b"a" * 50_000 + b"\n")
            self.assertTrue(lr.copytruncate(self.log, 1_000))
            os.write(fd, b"after\n")
        finally:
            os.close(fd)
        with open(self.log, "rb") as f:
            self.assertEqual(f.read(), b"after\n")  # no sparse hole

    def test_fd_path_resolves_regular_file_only(self):
        with open(self.log, "ab") as f:
            self.assertEqual(os.path.realpath(lr.fd_path(f.fileno())),
                             os.path.realpath(self.log))
        r, w = os.pipe()
        try:
            self.assertIsNone(lr.fd_path(r))
        finally:
            os.close(r)
            os.close(w)
        self.assertIsNone(lr.fd_path(987))

    def test_rotate_all_is_non_fatal(self):
        self.write_lines(1000)
        os.chmod(self.tmp.name, 0o500)  # cannot create .1.tmp
        try:
            self.assertEqual(lr.rotate_all([("path", self.log)], 1_000), [])
        finally:
            os.chmod(self.tmp.name, 0o700)
        self.assertEqual(os.path.getsize(self.log), 100_000)  # original intact

    def test_cli_path_mode(self):
        self.write_lines(1000)
        env = dict(os.environ, CLAUDE_REMOTE_LOG_MAX_BYTES="2000")
        r = subprocess.run([sys.executable, os.path.join(BIN, "claude-remote-logrotate"),
                            self.log], env=env)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(os.path.getsize(self.log), 0)
        self.assertLessEqual(os.path.getsize(self.log + ".1"), 2000)


class LauncherIntegrationTest(unittest.TestCase):
    """Run the real launcher with a fake `claude` and launchd-style log redirection."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.out = os.path.join(d, "claude-remote.out.log")
        self.err = os.path.join(d, "claude-remote.err.log")
        self.stop = os.path.join(d, "stop")
        self.fake = os.path.join(d, "claude")
        with open(self.fake, "w") as f:
            f.write(textwrap.dedent("""\
                #!/bin/sh
                if [ "$1" = "--version" ]; then echo "9.9.9 (Claude Code)"; exit 0; fi
                # emulate the TUI repaint spam until told to stop
                while [ ! -f "%s" ]; do
                    i=0
                    while [ $i -lt 200 ]; do
                        echo "Continue coding in the Claude mobile app ... space to show QR code"
                        i=$((i+1))
                    done
                    sleep 0.05
                done
                """ % self.stop))
        os.chmod(self.fake, 0o755)
        # A pre-existing oversized log, like the 1.5GB one on studio.
        with open(self.out, "wb") as f:
            f.write(b"old line\n" * 50_000)  # 450_000 bytes

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra):
        env = dict(os.environ,
                   CLAUDE_BIN=self.fake,
                   CLAUDE_REMOTE_ENV_FILE=os.path.join(self.tmp.name, "none.env"),
                   CLAUDE_REMOTE_HOST="test",
                   CLAUDE_REMOTE_LOG_MAX_BYTES="20000",
                   CLAUDE_REMOTE_LOG_INTERVAL="1")
        env.pop("CLAUDE_REMOTE_DIR", None)
        env.update(extra)
        return env

    def start(self, **extra):
        # Same shape as launchd: fds 1/2 opened O_APPEND on regular files.
        out = os.open(self.out, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        err = os.open(self.err, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            return subprocess.Popen([os.path.join(BIN, "claude-remote"), "--spawn", "x"],
                                    stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                    env=self.env(**extra), cwd=self.tmp.name)
        finally:
            os.close(out)
            os.close(err)

    def watchers(self, pid):
        r = subprocess.run(["pgrep", "-f", "claude-remote-logrotate.*--watch-pid %d" % pid],
                           capture_output=True, text=True)
        return r.stdout.split()

    def test_rotates_existing_and_growing_log_then_exits(self):
        p = self.start()
        try:
            # first pass at startup trims the oversized pre-existing log
            self.assertTrue(wait_for(lambda: os.path.exists(self.out + ".1")))
            # the daemon keeps writing; periodic passes keep the file bounded
            time.sleep(3)
            self.assertEqual(len(self.watchers(p.pid)), 1)
            sizes = []
            for _ in range(10):
                sizes.append(os.path.getsize(self.out))
                time.sleep(0.3)
            # without rotation the spam would be several MB by now
            self.assertLess(max(sizes), 2_000_000)
            self.assertLessEqual(os.path.getsize(self.out + ".1"), 20000)
        finally:
            open(self.stop, "w").close()
            p.wait(timeout=10)
        # watcher notices the daemon is gone and exits (POLL is 5s)
        self.assertTrue(wait_for(lambda: not self.watchers(p.pid), timeout=15))

    def test_disabled_by_env(self):
        p = self.start(CLAUDE_REMOTE_LOG_ROTATE="0")
        try:
            time.sleep(1.5)
            self.assertEqual(self.watchers(p.pid), [])
            self.assertFalse(os.path.exists(self.out + ".1"))
        finally:
            open(self.stop, "w").close()
            p.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
