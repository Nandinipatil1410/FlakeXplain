"""Serve a real, local FTP fixture with the pinned Conan suite's historical replies.

The public Rebex demo server changed its diagnostic text. This fixture restores
that external service contract without modifying Conan, its tests, or ftplib.
The workflow fetches the real demo readme before routing the hostname locally.
This is a controlled-service experiment, not an unchanged live-service replica.
"""
import argparse
from pathlib import Path

from pyftpdlib.authorizers import AuthenticationFailed, DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class HistoricalAuthorizer(DummyAuthorizer):
    def validate_authentication(self, username, password, handler):
        try:
            super().validate_authentication(username, password, handler)
        except AuthenticationFailed:
            raise AuthenticationFailed("User cannot log in.")


class HistoricalHandler(FTPHandler):
    def ftp_RETR(self, file):
        if not self.fs.isfile(file):
            self.respond("550 The system cannot find the file specified.")
            return
        return super().ftp_RETR(file)


def make_server(root, port=21):
    root = Path(root).resolve()
    if not (root / "pub/example/readme.txt").is_file():
        raise ValueError("The authentic Rebex readme fixture is missing")
    authorizer = HistoricalAuthorizer()
    # Public demo credentials used verbatim by upstream tests; read-only access.
    authorizer.add_user("demo", "password", str(root), perm="elr")
    HistoricalHandler.authorizer = authorizer
    HistoricalHandler.passive_ports = range(30000, 30100)
    return FTPServer(("127.0.0.1", port), HistoricalHandler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=21)
    args = parser.parse_args()
    make_server(args.root, args.port).serve_forever()


if __name__ == "__main__":
    main()
