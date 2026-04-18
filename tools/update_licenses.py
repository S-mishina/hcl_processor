import subprocess
import re
from pathlib import Path

LICENSE_FILE = Path("third_party_licenses.md")
START_TAG = "<!-- LICENSE-LIST:START -->"
END_TAG = "<!-- LICENSE-LIST:END -->"

import sys

def get_license_table():
    """Run pip-licenses and get the markdown output."""
    try:
        # Run pip-licenses via python -m piplicenses to ensure it's found in the current environment
        result = subprocess.run(
            [sys.executable, "-m", "piplicenses", "--format=markdown"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running pip-licenses: {e}")
        return None
    except FileNotFoundError:
        print("pip-licenses not found. Please install it with 'poetry add --group dev pip-licenses'")
        return None

def update_markdown():
    if not LICENSE_FILE.exists():
        print(f"{LICENSE_FILE} not found.")
        return

    new_table = get_license_table()
    if not new_table:
        return

    content = LICENSE_FILE.read_text()
    
    # regex to find content between tags
    pattern = re.compile(
        f"{re.escape(START_TAG)}.*?{re.escape(END_TAG)}",
        re.DOTALL
    )
    
    new_content = pattern.sub(
        f"{START_TAG}\n{new_table}\n{END_TAG}",
        content
    )
    
    if content != new_content:
        LICENSE_FILE.write_text(new_content)
        print(f"Successfully updated {LICENSE_FILE}")
    else:
        print(f"No changes needed for {LICENSE_FILE}")

if __name__ == "__main__":
    update_markdown()
