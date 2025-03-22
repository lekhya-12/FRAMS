import os

# Folders to check for usage
STATIC_DIR = "static"
TEMPLATES_DIR = "templates"
EXTENSIONS = [".html", ".js", ".css", ".py"]

# Get all static files
static_files = []
for root, _, files in os.walk(STATIC_DIR):
    for file in files:
        static_files.append(os.path.relpath(os.path.join(root, file)))

# Check if static files are used in project files
unused_files = []
for file in static_files:
    found = False
    for root, _, files in os.walk(TEMPLATES_DIR):
        for project_file in files:
            if any(project_file.endswith(ext) for ext in EXTENSIONS):
                with open(os.path.join(root, project_file), "r", errors="ignore") as f:
                    if file in f.read():
                        found = True
                        break
        if found:
            break
    if not found:
        unused_files.append(file)

# Print unused files
if unused_files:
    print("Unused static files:")
    for file in unused_files:
        print(file)
else:
    print("No unused static files found.")
