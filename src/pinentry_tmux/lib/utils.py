def get_pid_environ(pid: int) -> dict[str, str]:
    """Get the environment variables of a process by its PID."""
    environ_path = f"/proc/{pid}/environ"
    with open(environ_path, "rb") as f:
        environ_data = f.read()
    environ: dict[str, str] = {}
    for var in environ_data.split(b"\0"):
        if b"=" in var:
            key, value = var.split(b"=", 1)
            environ[key.decode()] = value.decode()
    return environ
