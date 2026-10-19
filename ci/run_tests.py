import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "ci-reports"

API_URL = "http://127.0.0.1:18000"
RESOURCE_URL = "http://127.0.0.1:18001"
PROCESSING_URL = "http://127.0.0.1:18002"


def service_environment(**settings):
    environment = os.environ.copy()

    for name in (
        "JWT_SECRET",
        "RESOURCE_JWT_SECRET",
        "PROCESSING_JWT_SECRET",
    ):
        environment.pop(name, None)

    environment.update(settings)
    return environment


def wait_for_service(process, url, expected_name):
    for _ in range(40):
        if process.poll() is not None:
            raise RuntimeError(f"{expected_name} exited during startup")

        try:
            with urlopen(f"{url}/health", timeout=1) as response:
                data = json.load(response)

                if data.get("service") == expected_name:
                    print(f"{expected_name} is ready", flush=True)
                    return
        except (URLError, TimeoutError, ValueError):
            pass

        time.sleep(0.5)

    raise RuntimeError(f"{expected_name} did not become ready")


def start_service(name, module, port, environment, processes, logs):
    log_file = (REPORTS_DIR / f"{name}.log").open("w", encoding="utf-8")
    logs.append(log_file)

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "uvicorn",
            f"{module}:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    processes.append(process)

    wait_for_service(
        process,
        f"http://127.0.0.1:{port}",
        name,
    )


def run_tests(marker, report_name, environment):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-m",
            marker,
            f"--junitxml={REPORTS_DIR / report_name}",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
    )

    return result.returncode


def main():
    REPORTS_DIR.mkdir(exist_ok=True)

    processes = []
    logs = []

    try:
        # Reset only the database belonging to this checkout.
        subprocess.run(
            [sys.executable, "-m", "resource_service.seed"],
            cwd=ROOT,
            check=True,
        )

        # Generate fresh development secrets for each CI run.
        user_secret = secrets.token_hex(32)
        resource_secret = secrets.token_hex(32)
        processing_secret = secrets.token_hex(32)

        start_service(
            "resource-service",
            "resource_service.main",
            18001,
            service_environment(
                RESOURCE_JWT_SECRET=resource_secret,
            ),
            processes,
            logs,
        )

        start_service(
            "processing-service",
            "processing_service.main",
            18002,
            service_environment(
                RESOURCE_JWT_SECRET=resource_secret,
                PROCESSING_JWT_SECRET=processing_secret,
                RESOURCE_SERVICE_URL=RESOURCE_URL,
            ),
            processes,
            logs,
        )

        start_service(
            "application-api",
            "application_api.main",
            18000,
            service_environment(
                JWT_SECRET=user_secret,
                RESOURCE_JWT_SECRET=resource_secret,
                PROCESSING_JWT_SECRET=processing_secret,
                RESOURCE_SERVICE_URL=RESOURCE_URL,
                PROCESSING_SERVICE_URL=PROCESSING_URL,
            ),
            processes,
            logs,
        )

        test_environment = service_environment(
            APPLICATION_API_URL=API_URL,
        )

        functional_status = run_tests(
            "not security",
            "functional.xml",
            test_environment,
        )

        security_status = run_tests(
            "security",
            "security.xml",
            test_environment,
        )

        if functional_status != 0 or security_status != 0:
            print("One or more test suites failed", flush=True)
            return 1

        print("All functional and security tests passed", flush=True)
        return 0

    except Exception as error:
        print(f"CI test runner error: {error}", file=sys.stderr)
        return 1

    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        for log_file in logs:
            log_file.close()


if __name__ == "__main__":
    sys.exit(main())
